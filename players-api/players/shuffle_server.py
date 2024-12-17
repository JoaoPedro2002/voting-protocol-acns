from lbvs_lib.scheme_algorithms import count
from lbvs_lib.serializers import deserialize_encrypted_ballot, serialize_shuffle_proof, deserialize_pk, deserialize_dk

from app import app
from classes import *

@app.post("/shuffler/setup")
def setup(setup_params: ShuffleServerSetup):
    pk = deserialize_pk(setup_params.instance.pk.model_dump(mode="json"))
    dk = deserialize_dk(setup_params.dk.model_dump(mode="json"))
    print(pk)
    print(dk)

@app.get("/shuffler/counting")
def counting_phase(ballots: list[EncryptedBallot]) -> bool:
    evs = map(deserialize_encrypted_ballot, ballots)
    # get dk
    dk = (None, None, None)
    proof = count(dk, evs)
    return serialize_shuffle_proof(proof)


