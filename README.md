# Evote Ranking

(derived from https://github.com/mdipierro/evote)

This module contains the ranking algorithms used by the Evote software (@2008-2019)
It also include an implementation of the EVote workflow for secure elections (improved).

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

- fully transparent (all files are always visible)
- fully anonymous (including to the system administrator)
- prevent vote tampering ($)
- prevent ballot stuffing ($)
- voters can check their own vote is properly recorded
- everybody can verify and recount the election
- prevent voters from making false claims

($ = technically possible but would be detected by voters and observers)

Notice the entire folder structure can be made public during the election without compromising the election. In fact it should be made public to allow voter to check their own vote is properly recorded and the election is not been tampered with.

Our implementation can easily scale to hundreads of thousands of voters. With some minor tweaks, like using a DB instad of a filesystem, it could scale to millions of voters.

### How it works

This system is designed to very closely mimic paper based voting sign some added security.

First of all we need two sets of public/private key pairs, which we can generate with 
openssl or programmatically with, for example, `human_security`:

```
from human_security import HumanRSA             `
h1 = HumanRSA()
h1.generate()
public_pem_1 = h1.public_pem()
private_pem_1 = h1.private_pem()

h2 = HumanRSA()
h2.generate()
public_pem_1 = h2.public_pem()
private_pem_1 = h2.private_pem()
```

`public_pem_1` and `public_pem_2` can be made public right away. The first allows the voters to check their
own vote is not tampered with. The second allows voters to check all the ballot signatures originated from
the system and not some malicious third party.

The system administrator should always have access to `public_pem_1` which is used to encrypt voted ballots and
`private_pem_2` which is used to sign them. Notice anybody could encrypt fake ballots because `public_pem_1` is public, but only the holder of `private_pem_2` can sign them and only the holder of `private_pem_1` can decrypt them.

Only at election closing the system administrator should be given `private_pem_1` which allows to
decrypt the ballots.

Setup the election:

```
>>> from evote_ranking import (instant_runoff, Workflow)
>>> folder = '/path/to/election/data'
>>> args = (folder, public_pem_1, private_pem_2)
>>> Workflow(*ags).setup()
```

This will create the following subfolders of `folder`:

- `blank_ballots`: which will store un-encrypted blank ballots (each with a number and a uuid)
- `voting_ballots`: blank ballots are moved here while a vote is recorded
- `encrypted_ballots`: stores encrypted voted ballots
- `decrypted_ballots`: stored decrypted voted ballots
- `signatures': for every encrypted voted ballot it stores a file with its signature
- `voters`: stores one file with the state of each voter (voted=True/False)

During each election the voters will rank candidates so EVote records who the candidates are:

```
>>> candidates = ['Tim','John','Matt']
>>> Workflow(*args).register_candidates(candidates)
```

They are stored in "candidates.json".

Then we record each voter:                       

```            
>>> for k in range(10):
>>>    Workflow(*args).register_voter(voter_id='voter-%i' % k)
```

When calling each functon we pass a `voter_id` that uniquely identifies the voter.

Notice we are not concerned with authentication of the voters.
We assume this is done by some third party UI and a `voter_id` has already been assigned to each voter.

EVote needs to prevent the same voter 
from voting twice therefore it hashes the `voter_id` and creates a json file
in the voters folder. The name of the file is the hash of the `voter_id`:
The file "voters/{voter-id-hash}.json" only stores {"voted": False}.

We then create the ballots (assuming 10 voters):

```
>>> Workflow(*args).create_ballots(10)
```

Ballot file names conform to this pattern:

    {status}_ballots/ballot.{number}.{status}.{content-hash}.json

Ballot signatures file names conform to this:

    signatures/ballot.{number}.{status}.{content-hash}.signature

(only status == encrypted ballots have signatures)

**Notice that at no time EVote stores any link between a ballot and a voter, not even the `voter_id` hash**

When the election opens, votes are recorded. For example 'voter-1' prefers Matt over Tim over John:

```
>>> receipt = Workflow(*args).cast_vote('voter-1', ['Matt', 'Tim','John'])
```

The process of recoding votes work as follows:

- lock the voter file
- pick a random blank ballot and move it in the `voting_ballots` folder
- store the vote in the ballot, encrypt it with the public key and write it in the `encrypted_ballots` folder
- generates a signatue for the voted ballot and stores it in the signatures folder
- mark the voter file with voted=True and unlock the file

If anything fails we restore the voter file and move the blank ballot in the `blank_ballots` folder
Notice the ballot is picked at random and not linked to the voter.

Also there is no information stored about the voter anywere other than a link between the hash of the voter unique identified and whether he/she has voted or not.

`cast_vote` returns a recept which contains:

```
>>> ballot_name, ballot_content, ballot_signatue = receipt
```

This information should be given to the voter as receipt, so that the voter can verify:

- which one is his/her ballot ballot
- that the ncrypted voted ballot was properly signed
- that the corresponding decrypted ballot has the same content as its voted ballot

Notice the purpose of the signature files is exclusively to prevent voters to fraudolently make up
fake ballots and claim their vote was not propery counted.

When the election closes the administrator must be provided with the `private_key_1` and all ballots are decrypted 
and stored in the `decrypted_ballots` folder:

```            
Workflow(*args).decrypt_ballots(private_pem_1)
```

The content of all folders should be made public so that:

- everybody can re-count the election
- everybody can verify the number of voters who voted matches number of voted ballots
- everybody can check the ballot serial numbers and check no ballots were created or destroyed
- everybody can re-encrypt decrypted ballots and check they were not tampered with 
- voter with a receipt can verify their own ballot matches the ballot in their receipt

Recounting the election is easy:

```            
results = Workflow(*args).count_votes(instant_runoff)
```

Here we used the instant runoff algorithm. The results are a list of (score, candidate) where the first
element if the winner and the last element is the loser.

### Caveats

Theoretically it is possible to deanonimize the votes if one can map `voter_id`s to voters and if one can correlate the times when a ballot is saved with the time when a voter file changed. To prevent this kind of vulnerability we recommend using an anonimized `voter_id` to uniquely identify the users. Also the administrator may want to postpone making the `encrypted_ballots` folder public until after the election closes and only make public its directly listing without timestamps. It is also advisable to touch all files just before closing the election so any information that may be used for timing attacks is lost forever.

The system administror could delete a voted ballot, make up and sign a fradolent one. Yet is this were two happen it would be detected because the new ballot would not match the signature received by the voter in the receipt. Also any observer would note that files are being deleted/replaced in the `encrypted_ballots` folder.

For added security the administrators may want to log the names of created files in a separate location for cross-checking. An idea would be to log the file creation in a blockchain but make sure not to introduce any timing attack as discussed earlier.

## License

BSD
