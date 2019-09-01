import os
import json
import hashlib

from filelock import FileLock


class Workflow:
    def __init__(self, workdir):
        self.workdir = workdir
        os.mkdir(os.path.join(workdir, 'blank_ballots'))  # ballots avaliable
        os.mkdir(os.path.join(workdir, 'voting_ballots')) # ballots not available
        os.mkdir(os.path.join(workdir, 'voted_ballots'))  # ballots voted
        os.mkdir(os.path.join(workdir, 'voters'))

    def register_candidates(self, candidates):
        filename = os.path.join(self.workdir, 'candidates.json')
        with open(filename, 'w') as fp:
            json.dump(candidates, fp)
        
    def register_voter(self, voter_name):
        voter_code = hashlib.md5(voter_name).hexdigest()
        filename = os.path.join(self.workdir, 'voters', voter_code+'.json')
        with open(filename, 'w') as fp:
            json.dump({'voted': False}, fp)
 
    def create_ballots(self, number, start=1):
        for k in range(start, start+numbe):
            ballot = {"number": k, "preferences": []}
            serial_ballot = json.dumps(ballot)
            signature = hashlib.md5(serial_ballot).hexdigest()
            ballot_name = 'ballot-%.6i-%s.json' % (k, signature)
            filename = os.path.join(self.workdir, 'blank_ballots', ballot_name)
            with open(filename, 'w') as fp:
                fp.write(serial_ballot)

    def cast_vote(self, voter_name, preferences):
        # get candidates
        filename = os.path.join(self.workdir, 'candidates.json')
        with open(filename, 'r') as fp:
            candidates = json.load(fp)
        # convert voter_name to votercode
        voter_code = hashlib.md5(voter_name).hexdigest()
        voter_filename = os.path.join(self.workdir, 'voters', voter_code+'.json')
        if not os.path.exists(voter_filename):
            raise RuntimeError('Voter is not allowed to vote')
        # lock the voter information
        lock = FileLock(voter_filename)
        try:
            with lock:
                with open(voter_filename, 'r') as fp:
                    voter_info = json.load(fp)
                    if voter_info['voted']:
                        raise RuntimeError('Voter has voted already')
                    ballot, ballot_name = self.pick_random_ballot()
                    ballot['preferences'] = prefences
                    voter
        with open(filename, 'w') as fp:
            fp.write(json.dumps({'voted': False, 'voting': False}))
    
               
 
