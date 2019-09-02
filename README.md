# Evote Ranking

This module contains the ranking algorithms used by the Evote software (@2008-2019)
It also include an implementation of the EVote workflow for secure elections

## Ranking algorithms

The algorithms are:

- `simple_majority`
- `instant_runoff`
- `borda algorithm`
- `shultze algorithm`

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

In all cases higher metric means higher preferences.
In the `simple_majority` case the metric is the simply the number of first votes.
In the schulze case the metric is just a progressive number.

[Read more](https://en.wikipedia.org/wiki/Ranked_voting)

## Secure election workflow

By secure elections we mean:

- fully anonymous
- prevent vote tampring
- prevent ballot stuffing
- voters can check their own vote is properly recorded
- ballots can be published to allow everybody to verify and recount the election
- the entire election can be made public during the election without compromising the election. In fact it should be made public to allow voter to check their own vote is probebly recorded and the election is not been tampered with.
- can easily scale to hundreads of thousands of votes (more with some minor tweaks, like using a DB instad of a filesystem).

### How it works

First of all we need a public/private key pair, which we can generate with 
openssl or programmatically with, for example, `human_security`:

```
from human_security import HumanRSA             
h = HumanRSA()
h.generate()
public_pem = h.public_pem()
private_pem = h.private_pem()
```

The public key will be used to encrypt the ballots and the private one will be used when the election 
closes, to decrypt the ballots. The system administrator should keep the `private_key` private until
election closes. Notice that the system administrator, because he/she holds the `private_key` has the power to
count the election before it closes but he/she does not have the power to break anonimity or
tamper with the election.

Setup the election:

```
>>> from evote_ranking import (instant_runoff, Workflow)
>>> folder = '/path/to/election/data'
>>> Workflow(folder, public_pem).setup()
```

This will create the following subfolders of `folder`:

- `blank_ballots`: which will store un-encrypted blank ballots (each with a number and a uuid)
- `voting_ballots`: blank ballots are moved here while a vote is recorded
- `encrypted_ballots`: stores encrypted voted ballots
- `decrypted_ballots`: stored decrypted voted ballots
- `voters`: stores one file with the state of each voter (voted=True/False)

During each election the voters will rank candidates so EVote records who the candidates are:

```
>>> candidates = ['Tim','John','Matt']
>>> Workflow(folder, public_pem).register_candidates(candidates)
```

They are stored in "candidates.json".

Then we record each voter:                       

```            
>>> for k in range(10):
>>>    Workflow(folder, public_pem).register_voter(voter_id='voter-%i' % k)
```

When calling each functon we pass a `voter_id` that uniquely identifies the voter.

Notice we are not concerned with authentication of the voters.
We assume this is done by some third party UI and a `voter_id` has already been assigned to each voter.

EVote needs to prevent the same voter 
from voting twice therefore it hashes the `voter_id` and creates a json file
in the voters folder. The name of the file is the hash of the `voter_id`:
The file "voters/{voter-id-hash}.json" only stores {"voted": False}.

We then create the ballots (assumgin 10 voters):

```
>>> Workflow(folder, public_pem).create_ballots(10)
```

Each ballot is a json file that contains a serial number, a unique uuid, and its name looks like:

`blank_ballots/ballot.{number}.blank.{content-hash}.json`

**Notice that at no time EVote stores any link between a ballot and a voter, not even the `voter_id` hash**

When the election opens, votes are recorded. For example 'voter-1' prefers Matt over Tim over John:

```
>>> filename, ballot = Workflow(folder, public_pem).cast_vote('voter-1', ['Matt', 'Tim','John'])
```

The process of recoding votes work as follows:

- lock the voter file
- pick a random blank ballot and move it in the `voting_ballots` folder
- store the vote in the ballot, encrypt it with the public key and write it in the `encrypted_ballots` folder
- mark the voter file with voted=True and unlock the file

If anything fail we restore the voter file and move the blank ballot in the `blank_ballots` folder
Notice the ballot is picked at random and not linked to the voter.

Also there is no information stored about the voter anywere other than a link between the hash of the voter unique identified and whether he/she has voted or not.

Both the `blank_ballots` and the `encrypted_ballots` can be made public without violatity security.
The `cast_vote` method returns the name of the encrypted ballot and the decrypted content of the ballot.
This information can safely be returned to the voter as receipt, so that the voter can verify:

- which one is his/her ballot ballot
- that the dorresponding decrypted ballot has the same content as its voted ballot (when the election closes) 

We strongly recommend digitally signing receipts with a separate public key before returning recepts to voters
to prevent mailicious voters from conterfitting receipts and falsely claiming their vote was tampetered with.

When the election closes the administrator must provide the private key and all ballots are decrypted 
and stored in the `decrypted_ballots` folder:

```            
Workflow(folder, public_pem).decrypt_ballots(private_pem)
```

The content of the folder should be made public so that:

- everybody can re-count the election
- everybody can verify the number of voters who voted matches number of voted ballots
- everybody can check the ballot serial numbers and check no ballots were created or destroyed
- everybody can re-encrypt decrypted ballots and check they were not tampered with 
- voter with a receipt can verify their own ballot matches the ballot in their receipt

Recounting the election is easy:

```            
results = Workflow(folder, public_pem).count_votes(instant_runoff)
```

Here we used the instant runoff algorithm. The results are a list of (score, candidate) where the first
element if the winner and the last element is the loser.

### Caveats

Theoretically it is possible to deanonimize the votes if one can map `voter_id`s to voters and if one can correlate the times when a ballot is saved with the time when a voter file changed. To prevent this kind of vulnerability we recommend using an anonimized `voter_id` to uniquely identify the users. Also the administrator may want to postpone making the `encrypted_ballots` folder public until after the election closes and only make public its directly listing without timestamps. It is also advisable to touch all files just before closing the election so any information that may be used for timing attacks is lost forever.

## License

BSD
