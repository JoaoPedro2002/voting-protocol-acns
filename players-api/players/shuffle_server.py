from lbvs_lib.scheme_algorithms import count
from lbvs_lib.serializers import deserialize_encrypted_ballot, serialize_shuffle_proof

from app import app
from classes import *

@app.get("/shuffler/counting")
def counting_phase(ballots: list[EncryptedBallot]) -> bool:
    evs = map(deserialize_encrypted_ballot, ballots)
    # get dk
    dk = (None, None, None)
    proof = count(dk, evs)
    return serialize_shuffle_proof(proof)


