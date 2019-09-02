import re
import os
import json
import hashlib
import datetime
import uuid
import random
import shutil
from pathlib import Path

from filelock import FileLock

class EVoteError(RuntimeError): pass

class Workflow:

    re_blank = re.compile(r'^ballot\.\d+\.blank\.[\w-]+\.json$')
    re_encrypted = re.compile(r'^ballot\.\d+\.voted\.encrypted\.[\w-]+\.json$')
    re_decrypted = re.compile(r'^ballot\.\d+\.voted\.[\w-]+\.json$')

    def __init__(self, workdir, secret_key):
        self.workdir = workdir
        self.secret_key = secret_key

    def setup(self):
        os.mkdir(os.path.join(self.workdir, 'blank_ballots'))  # ballots avaliable
        os.mkdir(os.path.join(self.workdir, 'voting_ballots')) # ballots not available
        os.mkdir(os.path.join(self.workdir, 'encrypted_ballots'))  # ballots voted
        os.mkdir(os.path.join(self.workdir, 'decrypted_ballots'))  # ballots voted
        os.mkdir(os.path.join(self.workdir, 'voters'))

    def hash(self, data):
        return hashlib.md5(data.encode()).hexdigest()

    def verify_integrity(self, name, serialized_ballot):
        # not implemented error
        return

    def get_path(self, ballot_type, name):
        return os.path.join(self.workdir, ballot_type + '_ballots', name)
    
    def register_candidates(self, candidates):
        filename = os.path.join(self.workdir, 'candidates.json')
        with open(filename, 'w') as fp:
            json.dump(candidates, fp)
        
    def register_voter(self, voter_id):
        voter_code = self.hash(voter_id)
        filename = os.path.join(self.workdir, 'voters', voter_code+'.json')
        with open(filename, 'w') as fp:
            json.dump({'voted': False}, fp)
 
    def create_ballots(self, number, start=1, metadata=None):
        for k in range(start, start+number):
            ballot = {"number": k,
                      "creation_timestamp": datetime.datetime.utcnow().isostring(),
                      "uuid": str(uuid.uuid4()),
                      "preference": [],                       
                      "metadata": metadata}
            serialized_ballot = json.dumps(ballot)
            signature = self.hash(serialized_ballot)
            ballot_name = 'ballot.%.6i.blank.%s.json' % (k, signature)
            ballot_path = self.get_path('blank', ballot_name)
            with open(ballot_path, 'w') as fp:
                fp.write(serialized_ballot)

    def pick_random_ballot(self):
        folder = os.path.join(self.workdir, 'blank_ballots')
        ballot_names = [name for name in os.listdir(folder) if self.re_blank.match(name)]
        ballot_name = random.choice(ballot_names)
        source_path = self.get_path('blank', ballot_name),
        destination_path = self.get_path('voting', ballot_name)
        shutil.move(source_path, destination_path)
        with open(destination_path) as fp:
            serialized_ballot = fp.read()
            self.verify_integrity(ballot_name, serialized_ballot)
            ballot = json.loads(serialized_ballot)
        return ballot_name, ballot

    def encrypt_serialized_ballot(self, serialized_ballot):
        encrypted_ballot = '<encrypted>' + serialized_ballot + '<encrypted>'
        return encrypted_ballot 

    def decrypt_serialized_ballot(self, serialized_ballot):
        decrypted_ballot = serialized_ballot[11:-11]
        return decrypted_ballot 

    def save_voted_ballot(self, ballot):
        serialized_ballot = json.dumps(ballot)
        encrypted_ballot = self.encrypt_serialized_ballot(serialized_ballot)
        signature = self.hash(encrypted_ballot)
        ballot_name = 'ballot.%.6i.voted.encrypted.%s.json' % (ballot['number'], signature)        
        new_ballot_path = self.get_path('encrypted', ballot_name)
        with open(new_ballot_path, 'w') as fp:
            fp.write(encrypted_ballot)
        return ballot_name, serialized_ballot


    def cast_vote(self, voter_id, preference):
        # get candidates
        filename = os.path.join(self.workdir, 'candidates.json')
        with open(filename, 'r') as fp:
            candidates = json.load(fp)
        # convert voter_id to votercode
        voter_code = self.hash(voter_id)
        voter_filename = os.path.join(self.workdir, 'voters', voter_code+'.json')
        if not os.path.exists(voter_filename):
            raise RuntimeError('Voter is not allowed to vote')
        # lock the voter information
        lock = FileLock(voter_filename)
        with lock:
            try:
                # check the user has not voted already
                with open(voter_filename, 'r') as fp:
                    voter_info = json.load(fp)
                if voter_info['voted']:
                    raise EVoteError('Voter has voted already')
                # pick a random ballot
                original_ballot_name, ballot = self.pick_random_ballot()
                # record votes
                ballot['preference'] = preference
                # save the voted ballot
                new_ballot_name, serialized_ballot = self.save_voted_ballot(ballot)
                # delete blank ballot
                os.unlink(self.get_path('voting', original_ballot_name))
                # record voter has voted
                voter_info['voted'] = True
                with open(voter_filename, 'w') as fp:
                    json.dump(voter_info, fp)
                return new_ballot_name, serialized_ballot
            except EVoteError:
                raise
            except Exception as original_exception:
                try:
                    voting_ballot_path = self.get_path('voting', original_ballot_name)
                    blank_ballot_path = self.get_path('blank', original_ballot_name)
                    voted_ballot_path = self.get_path('encrypted', new_ballot_name)
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

    def close_election(self):
        encrypted_ballots_folder = os.path.join(self.workdir, 'encrypted_ballots')
        ballot_names = [name for name in os.listdir(encrypted_ballots_folder) if self.re_encrypted.match(name)]
        for ballot_name in ballot_names:
            encrypted_path = self.get_path('encrypted', ballot_name)
            with open(encrypted_path) as fp:
                serialzied_encypted_ballot = fp.read()
                self.verify_integrity(ballot_name, serialized_decrypted_ballot)
            serialized_decrypted_ballot = self.decrypt_serialized_ballot(serialzied_encypted_ballot)
            signature = self.hash(serialized_decrypted_ballot)
            ballot_number = ballot_name.split('.')[1]
            ballot_name = 'ballot.%.6i.voted.%s.json' % (ballot_number, signature)
 
    def count_votes(self, alg):
        decrypted_ballots_folder = os.path.join(self.workdir, 'decrypted_ballots')
        ballot_names = [name for name in os.listdir(decrypted_ballots_folder) if self.re_decrypted.match(name)]
        preferences = []
        for ballot_name in ballot_names:
            decrypted_path = self.get_path('decrypted', ballot_name)
            with open(decrypted_path) as fp:
                serialized_decrypted_ballot = fp.read()
            self.verify_integrity(ballot_name, serialized_decrypted_ballot)
            data = json.loads(serialized_decrypted_ballot)
            preference = data['preference']
            preferences.append(preference)
        return alg(preferences)
