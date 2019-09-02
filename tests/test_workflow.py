import os
import uuid
import random
import random
import tempfile
from unittest import TestCase
from evote_ranking import (simple_majority, instant_runoff, borda, schulze, Workflow)
from human_security import HumanRSA

class EvoteWorkflowTest(TestCase):

    def test_workflow(self):

        h = HumanRSA()
        h.generate()
        public_pem = h.public_pem()
        private_pem = h.private_pem()

        with tempfile.TemporaryDirectory() as folder:
            random.seed(1)
            candidates = ['Tim','John','Matt']
            Workflow(folder, public_pem).setup()
            Workflow(folder, public_pem).create_ballots(10)
            Workflow(folder, public_pem).register_candidates(candidates)
            for k in range(10):
                Workflow(folder, public_pem).register_voter('voter-%i' % k)
            for k in range(9):
                random.shuffle(candidates)
                Workflow(folder, public_pem).cast_vote('voter-%i' % k, candidates)
            def func():
                Workflow(folder, public_pem).cast_vote('voter-%i' % 0, candidates)
            self.assertRaises(Exception, func)
            Workflow(folder, public_pem).decrypt_ballots(private_pem)
            results = Workflow(folder, public_pem).count_votes(instant_runoff)
            expected = [(9, 'Tim'), (4, 'Matt'), (2, 'John')]
            self.assertEqual(results, expected)
            self.assertEqual(len(os.listdir(os.path.join(folder, 'blank_ballots'))), 1)
            self.assertEqual(len(os.listdir(os.path.join(folder, 'encrypted_ballots'))), 9)
            self.assertEqual(len(os.listdir(os.path.join(folder, 'decrypted_ballots'))), 9)
