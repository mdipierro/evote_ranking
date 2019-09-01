from functools import reduce
import collections

__all__ = ['simple_majority', 'instant_runoff', 'borda', 'schulze']


def cmp(a, b):
    return (a > b) - (a < b)


def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K:
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K


def assert_valid(preference):
    """check no repeated candidate names in preference"""
    if len(preference) != len(set(preference)):
        raise ValueError('Invalid preference. Candidate name is repeated')

def simple_majority(preferences):
    """simple majority ranking"""
    votes = collections.defaultdict(int)
    for preference in preferences:
        if preference:
            votes[preference[0]] += 1
    votes_list = [(v, k) for k, v in votes.items()]
    votes_list.sort(reverse=True)
    return votes_list


def instant_runoff(preferences):
    """instant run-off ranking"""
    # winners is a list of (v,k) = (number of preferences, option number)
    # ordered from the candidate with the least preferences to the highest
    winners = []
    losers = set()
    allowed_options = reduce(
        lambda a, b: a | b, [set(preference) for preference in preferences])
    n = len(allowed_options)
    while len(winners) < n:
        # options maps candidates to count of ballots
        # who preferenced for that candidate in first place
        # after ignoring some candidates
        options = {}
        # important! options must be initialized to that all options
        # are present, even nobody choose them as their first option
        # else 0 counts would not be present
        for item in allowed_options:
            if not item in losers:
                options[item] = 0
        # for every ballot
        for preference in preferences:
            # check the preference for the ballot is valid
            assert_valid(preference)
            # for each voting option in this balloe
            for item in preference:
                # if the option(candidate) have not been
                # alreday discurded
                if not item in losers:
                    # count how many ballot have this option
                    # as first option
                    options[item] += 1
                    break

        # find the option(candidate) with the least number of
        # top preferences
        options_list = [(v, k) for (k, v) in options.items()]
        options_list.sort()
        minv = options_list[0][0]
        # discard this option and count again
        for (v, k) in options_list:
            if v == minv:
                losers.add(k)
                winners.insert(0, (v, k))
    return winners


def borda(preferences, mode='linear'):
    """borda ranking when mode=linear (default)"""
    if not mode in ('linear', 'fractional', 'exponential'):
        raise RuntimeError("mode not supported")
    winners = {}
    n = len(preferences[0])
    for preference in preferences:
        assert_valid(preference)
        for k, item in enumerate(preference):
            if mode == 'linear':
                delta = (n - k)
            elif mode == 'fractional':
                delta = 1.0 / (k + 1)
            elif mode == 'exponential':
                delta = n ** (n - k - 1)
            winners[item] = winners.get(item, 0) + delta
    winners = [(v, k) for (k, v) in winners.items()]
    winners.sort(reverse=True)
    return winners


def schulze(preferences):
    """schulze ranking algorithm"""
    d = {}
    p = {}
    candidates = list(reduce(
        lambda a, b: a & b,
        [set(preference) for preference in preferences]
        ))
    map_candid = dict((k, i) for (i, k) in enumerate(candidates))
    n = len(candidates)
    for i in range(n):
        for j in range(n):
            d[i, j] = p[i, j] = 0
    for preference in preferences:
        assert_valid(preference)
        for i in range(0, n - 1):
            for j in range(i + 1, n):
                key = (map_candid[preference[i]], map_candid[preference[j]])
                d[key] += 1
    for i in range(n):
        for j in range(n):
            if i != j:
                p[i, j] = d[i, j] if d[i, j] > d[j, i] else 0
    for i in range(n):
        for j in range(n):
            if i != j:
                for k in range(n):
                    if k != i and k != j:
                        p[j, k] = max(p[j, k], min(p[j, i], p[i, k]))
    winners = list(range(n))
    winners.sort(key=cmp_to_key(lambda i, j: cmp(p[i, j], p[j, i])))
    winners = [(i, candidates[k]) for (i, k) in enumerate(winners)]
    winners.reverse()
    return winners
