import os
import uuid
import random
import random
import tempfile
from unittest import TestCase
from evote_ranking import (simple_majority, instant_runoff, borda, schulze, Workflow)
from evote_ranking.workflow import EVoteError
from human_security import HumanRSA

class EvoteWorkflowTest(TestCase):

    def test_workflow(self):

        h1 = HumanRSA()
        h1.generate()
        public_pem_1 = h1.public_pem()
        private_pem_1 = h1.private_pem()

        h2 = HumanRSA()
        h2.generate()
        public_pem_2 = h2.public_pem()
        private_pem_2 = h2.private_pem()

        with tempfile.TemporaryDirectory() as folder:
            random.seed(1)
            args = (folder, public_pem_1, private_pem_2)

            candidates = ['Tim','John','Matt']
            Workflow(*args).setup()
            Workflow(*args).create_ballots(10)
            Workflow(*args).register_candidates(candidates)
            for k in range(10):
                Workflow(*args).register_voter('voter-%i' % k)
            for k in range(9):
                random.shuffle(candidates)
                Workflow(*args).cast_vote('voter-%i' % k, candidates)
            def func():
                Workflow(*args).cast_vote('voter-%i' % 0, candidates)
            self.assertRaises(EVoteError, func)
            Workflow(*args).decrypt_ballots(private_pem_1)
            results = Workflow(*args).count_votes(instant_runoff)
            expected = [(9, 'Tim'), (4, 'Matt'), (2, 'John')]
            self.assertEqual(results, expected)
            self.assertEqual(len(os.listdir(os.path.join(folder, 'blank_ballots'))), 1)
            self.assertEqual(len(os.listdir(os.path.join(folder, 'encrypted_ballots'))), 9)
            self.assertEqual(len(os.listdir(os.path.join(folder, 'decrypted_ballots'))), 9)
