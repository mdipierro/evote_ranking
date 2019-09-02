import re
import os
import json
import hashlib
import datetime
import uuid
import random
import shutil
import logging

from pathlib import Path

from filelock import FileLock
from human_security import HumanRSA

class EVoteError(RuntimeError): pass

class Workflow:

    re_blank = re.compile(r'^ballot\.\d+\.blank\.[\w]+\.json$')
    re_encrypted = re.compile(r'^ballot\.\d+\.encrypted\.[\w]+\.json$')
    re_decrypted = re.compile(r'^ballot\.\d+\.decrypted\.[\w]+\.json$')

    def __init__(self, workdir, public_key_1, private_key_2, logger=logging):
        self.workdir = workdir
        self.public_key_1 = public_key_1
        self.private_key_2 = private_key_2
        self.logger = logger        

    def setup(self):
        """creates all folders"""
        self.logger.info('BEGIN creating requied subfolders')
        os.mkdir(os.path.join(self.workdir, 'blank_ballots'))  # ballots avaliable
        os.mkdir(os.path.join(self.workdir, 'voting_ballots')) # ballots not available
        os.mkdir(os.path.join(self.workdir, 'encrypted_ballots'))  # ballots voted
        os.mkdir(os.path.join(self.workdir, 'decrypted_ballots'))  # ballots voted
        os.mkdir(os.path.join(self.workdir, 'signatures'))  # signatures of voted ballots
        os.mkdir(os.path.join(self.workdir, 'voters'))
        self.logger.info('END creating requied subfolders')

    def hash(self, data):
        """used to hash ballot content"""
        data = data.encode() if isinstance(data, str) else data
        return hashlib.md5(data).hexdigest()

    def verify_integrity(self, name, data):
        """check that content data of ballots matches hash in the name"""
        self.logger.info('verifying ballot integrity %s' % name)
        assert self.hash(data) == name.split('.')[3]

    def get_path(self, name, folder=None):
        """given ballot name, builds the full path to the ballot file (folder is optional)"""
        if not folder:
            folder = name.split('.')[2] + '_ballots'
        return os.path.join(self.workdir, folder, name)
    
    def register_candidates(self, candidates):
        """saves the names of election candidates in candidates.json"""
        self.logger.info('BEGIN registering cadidates')
        for candidate in candidates:
            self.logger.info('candidate:', candidate)
        filename = os.path.join(self.workdir, 'candidates.json')
        with open(filename, 'w') as fp:
            json.dump(candidates, fp)
        self.logger.info('END registering cadidates')
        
    def register_voter(self, voter_id):
        """regiters a new voter but creating a voters/{voter_code}.json file"""
        voter_code = self.hash(voter_id)
        self.logger.info('BEGIN registering voter' , voter_code)
        filename = os.path.join(self.workdir, 'voters', voter_code+'.json')
        with open(filename, 'w') as fp:
            self.logger.info(filename)
            json.dump({'voter_code': voter_code, 'voted': False}, fp)
        self.logger.info('BEGIN registering voter')

    def create_ballots(self, number, start=1, metadata=None):
        """creates a black ballot for each voter, can store optional metadata in the ballots"""
        self.logger.info('BEGIN creating blank ballots')
        for k in range(start, start+number):
            self.logger.info('creating ballot %.6i' % k)
            ballot = {"number": k,
                      "creation_timestamp": str(datetime.datetime.utcnow()),
                      "uuid": str(uuid.uuid4()),
                      "preference": [],
                      "metadata": metadata}
            serialized_ballot = json.dumps(ballot)
            ballot_hash = self.hash(serialized_ballot)
            ballot_name = 'ballot.%.6i.blank.%s.json' % (k, ballot_hash)
            ballot_path = self.get_path(ballot_name)
            with open(ballot_path, 'w') as fp:
                fp.write(serialized_ballot)
        self.logger.info('END creating blank ballots')

    def pick_random_ballot(self):
        """when a new voter is ready to vote pick a blank ballot at random, return the name and content"""
        folder = os.path.join(self.workdir, 'blank_ballots')
        ballot_names = [name for name in os.listdir(folder) if self.re_blank.match(name)]
        ballot_name = random.choice(ballot_names)
        source_path = self.get_path(ballot_name)
        destination_path = self.get_path(ballot_name, 'voting_ballots')
        shutil.move(source_path, destination_path)
        with open(destination_path) as fp:
            serialized_ballot = fp.read()
            self.verify_integrity(ballot_name, serialized_ballot)
            ballot = json.loads(serialized_ballot)
        self.logger.info('picked a random ballot %s' % ballot_name)
        return ballot_name, ballot

    def encrypt_serialized_ballot(self, serialized_ballot):
        """encrypts a serialized ballot using RSA self.public_key_1"""
        self.logger.info('encrypting ballot')
        h = HumanRSA()
        h.load_public_pem(self.public_key_1)
        encrypted_ballot = h.encrypt(serialized_ballot.encode())
        return encrypted_ballot

    def decrypt_serialized_ballot(self, serialized_ballot, private_key_1):
        """decrypts a ballot using the provided private_key_1"""
        self.logger.info('decrypting ballot')
        h = HumanRSA()
        h.load_private_pem(private_key_1)
        decrypted_ballot = h.decrypt(serialized_ballot).decode()
        return decrypted_ballot 

    def save_voted_ballot(self, ballot):
        """encrypts and saves a ballot and its signature file"""
        serialized_ballot = json.dumps(ballot)
        encrypted_ballot = self.encrypt_serialized_ballot(serialized_ballot)
        ballot_hash = self.hash(encrypted_ballot)
        ballot_name = 'ballot.%.6i.encrypted.%s.json' % (ballot['number'], ballot_hash)        
        self.logger.info('saving encryted voted ballot %s' % ballot_name)
        new_ballot_path = self.get_path(ballot_name)
        with open(new_ballot_path, 'wb') as fp:
            fp.write(encrypted_ballot)

        signature_name = 'ballot.%.6i.encrypted.%s.signature' % (ballot['number'], ballot_hash)
        self.logger.info('saving ballot digital signature %s' % ballot_name)
        signature_path = os.path.join(self.workdir, 'signatures', signature_name)
        h = HumanRSA()
        h.load_private_pem(self.private_key_2)
        signature = h.sign(encrypted_ballot)
        with open(signature_path, 'wb') as fp:
            fp.write(signature)       
        return ballot_name, serialized_ballot, signature


    def cast_vote(self, voter_id, preference):
        """records a vote:
        - check voter has not already voted
        - picks a random ballot
        - records the vote
        - stores the encrypted voted ballot
        - stores the signature for the encrypted voted ballot
        - marks the voter file as voted=True
        """
        # get candidates
        filename = os.path.join(self.workdir, 'candidates.json')
        with open(filename, 'r') as fp:
            candidates = json.load(fp)
        # convert voter_id to votercode
        voter_code = self.hash(voter_id)
        voter_filename = os.path.join(self.workdir, 'voters', voter_code+'.json')
        if not os.path.exists(voter_filename):
            raise EVoteError('Voter is not allowed to vote')
        # lock the voter information
        lock = FileLock(voter_filename+'.lock')
        with lock:
            # check the user has not voted already
            with open(voter_filename, 'r') as fp:                    
                data = fp.read()
            self.logger.info(voter_filename, repr(data))
            voter_info = json.loads(data)
            if voter_info['voted']:
                self.logger.info('voter has voted already')
                raise EVoteError('Voter has voted already')
            # pick a random ballot
            original_ballot_name, ballot = self.pick_random_ballot()
            # record votes
            ballot['preference'] = preference
            # save the voted ballot
            new_ballot_name, serialized_ballot, signature = self.save_voted_ballot(ballot)
            try:
                # delete blank ballot
                os.unlink(self.get_path(original_ballot_name, 'voting_ballots'))
                # record voter has voted
                voter_info['voted'] = True
                with open(voter_filename, 'w') as fp:
                    json.dump(voter_info, fp)
                return new_ballot_name, serialized_ballot, signature
            except EVoteError:
                raise
            except Exception as original_exception:
                try:
                    voting_ballot_path = self.get_path(original_ballot_name, 'voting_ballots')
                    blank_ballot_path = self.get_path(original_ballot_name)
                    voted_ballot_path = self.get_path(new_ballot_name)
                    # if the vote was not propery recorded - undo everything
                    if os.path.exists(voting_ballot_path):
                        shutil.move(voting_ballot_path, blank_ballot_path)
                        if os.path.exists(voted_ballot_path):
                            os.unlink(voted_ballot_path)
                        voter_info['voted'] = False
                        with open(voter_filename, 'w') as fp:
                            json.dump(voter_info, fp)                        
                    raise original_exception
                except Exception as new_exception:
                    raise new_exception

    def decrypt_ballots(self, private_key):
        """decripts all ballots"""
        self.logger.info('BEGIN decrypting ballots')
        encrypted_ballots_folder = os.path.join(self.workdir, 'encrypted_ballots')
        ballot_names = [name for name in os.listdir(encrypted_ballots_folder) if self.re_encrypted.match(name)]
        for ballot_name in ballot_names:
            self.logger.info('decrypting %s' % ballot_name)
            encrypted_path = self.get_path(ballot_name)
            with open(encrypted_path, 'rb') as fp:
                serialized_encrypted_ballot = fp.read()
                self.verify_integrity(ballot_name, serialized_encrypted_ballot)
            serialized_decrypted_ballot = self.decrypt_serialized_ballot(serialized_encrypted_ballot, private_key)
            ballot_hash = self.hash(serialized_decrypted_ballot)
            ballot_number = int(ballot_name.split('.')[1])
            ballot_name = 'ballot.%.6i.decrypted.%s.json' % (ballot_number, ballot_hash)
            self.logger.info('saving decrypted ballot %s' % ballot_name)
            decrypted_path = self.get_path(ballot_name)
            with open(decrypted_path, 'w') as fp:
                fp.write(serialized_decrypted_ballot)
        self.logger.info('END decrypting ballots')

    def count_votes(self, alg):
        """counts all votes stored in the decrypted ballots"""
        self.logger.info('BEGIN counting votes')
        decrypted_ballots_folder = os.path.join(self.workdir, 'decrypted_ballots')
        ballot_names = [name for name in os.listdir(decrypted_ballots_folder) if self.re_decrypted.match(name)]
        preferences = []
        for ballot_name in ballot_names:
            self.logger.info('counting balot %s' % ballot_name)
            decrypted_path = self.get_path(ballot_name)
            with open(decrypted_path) as fp:
                serialized_decrypted_ballot = fp.read()
            self.verify_integrity(ballot_name, serialized_decrypted_ballot)
            data = json.loads(serialized_decrypted_ballot)
            preference = data['preference']
            preferences.append(preference)
        self.logger.info('END counting votes')
        return alg(preferences)
