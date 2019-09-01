from unittest import TestCase
from evote_ranking import (simple_majority, instant_runoff, borda, schulze)


class EvoteTest(TestCase):

    def setUp(self):
        self.preferences = []
        for i in range(5): self.preferences.append(['A','C','B','E','D'])
        for i in range(5): self.preferences.append(['A','D','E','C','B'])
        for i in range(8): self.preferences.append(['B','E','D','A','C'])
        for i in range(3): self.preferences.append(['C','A','B','E','D'])
        for i in range(7): self.preferences.append(['C','A','E','B','D'])
        for i in range(2): self.preferences.append(['C','B','A','D','E'])
        for i in range(7): self.preferences.append(['D','C','E','B','A'])
        for i in range(8): self.preferences.append(['E','B','A','D','C'])

    def test_simple_majority(self):
        results = simple_majority(self.preferences)
        print(results)
        expected = [(12, 'C'), (10, 'A'), (8, 'E'), (8, 'B'), (7, 'D')]
        self.assertEqual(results, expected)

    def test_instant_runoff(self):
        results = instant_runoff(self.preferences)
        print(results)
        expected = [(45, 'A'), (19, 'C'), (8, 'E'), (8, 'B'), (7, 'D')]
        self.assertEqual(results, expected)

    def test_borda(self):
        results = borda(self.preferences)
        print(results)
        expected = [(147, 'E'), (143, 'A'), (137, 'B'), (134, 'C'), (114, 'D')]
        self.assertEqual(results, expected)
    
    def test_schulze(self):
        results= schulze(self.preferences)
        expected = [(4, 'E'), (3, 'A'), (2, 'C'), (1, 'B'), (0, 'D')]
        self.assertEqual(results, expected)
