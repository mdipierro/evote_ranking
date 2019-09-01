## Evote Ranking

This module contains the ranking algorithms used by the Evote software (@2008-2019)

The algorithms are:

- simple_majority
- instant_runoff
- borda algorithm
- shultze algorithm

All the algoithms take as input a list of preferences or votes. 
Each preference or vote is itself is a list of candidate sorted by prefernece.

For example imagine 3 election candicates 'A', 'B', and 'C' and 4 votes:

```
preferences = [
 ['A', 'B', 'C'], 
 ['A', 'B', 'C'],
 ['A', 'C', 'B'],
 ['B', 'A', 'C']]
```
The first and second voters prefers A over B over C.
The third voter prefers A over C over B.
The fourth voter prefers B ove A over C.

All the function returns is a sorted list of (metric, candidate)
The meaning of the metric is dependent of the algorithm.
The first list element contains the top ranking candidate (winner)
The last list element contains the bottom ranking candidate (loser)
The metric can be used to identify candidates with similar ranking.

[Read more](https://en.wikipedia.org/wiki/Ranked_voting)

## License

BSD
