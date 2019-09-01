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
        expected = [('C', 12), ('A', 10), ('E', 8), ('B', 8), ('D', 7)]
        self.assertEqual(results, expected)

    def test_instant_runoff(self):
        results = instant_runoff(self.preferences)
        print(results)
        expected = [(7, 'D'), (8, 'B'), (8, 'E'), (19, 'C'), (45, 'A')]
        self.assertEqual(results, expected)

    def test_borda(self):
        results = borda(self.preferences)
        print(results)
        expected = [(114, 'D'), (134, 'C'), (137, 'B'), (143, 'A'), (147, 'E')]
        self.assertEqual(results, expected)
    
    def test_schulze(self):
        results= schulze(self.preferences)
        expected = [(0, 'D'), (1, 'B'), (2, 'C'), (3, 'A'), (4, 'E')]
        self.assertEqual(results, expected)
