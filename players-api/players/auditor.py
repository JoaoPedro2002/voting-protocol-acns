from lbvs_lib.classes import NMOD_POLY_TYPE
from lbvs_lib.serializers import deserialize_shuffle_proof, deserialize_c_obj, serialize
from lbvs_lib.primitives import vericrypt, lib
from lbvs_lib.scheme_algorithms import verify
from lbvs_lib.utils import ev_equals, pv_equals

from app import app, SessionDep
from classes import DecipheredBallots


@app.get("/auditor/verify_ballots")
def verify_ballots() -> bool:
    evs_proofs_ballot_box = []
    evs_proof_code_server = []

    assert len(evs_proofs_ballot_box) == len(evs_proof_code_server)

    for i in range(len(evs_proofs_ballot_box)):
        ev_ballot_box, proof_ballot_box = evs_proofs_ballot_box[i]
        ev_code_server, proof_code_server = evs_proof_code_server[i]
        if not ev_equals(lib, ev_ballot_box, ev_code_server, vericrypt.context):
            return False
        if not pv_equals(lib, proof_ballot_box, proof_code_server, vericrypt.context):
            return False


@app.get("/auditor/verify_shuffle")
def counting_phase(
        deciphered_ballots: DecipheredBallots,
        session: SessionDep
) -> bool:
    proof = deserialize_shuffle_proof(deciphered_ballots.shuffle_proof.model_dump(mode="json"))
    # public key
    pk = (None, None, None)
    # encrypted votes
    evs = []
    # shuffled ballots
    ballots = [deserialize_c_obj(NMOD_POLY_TYPE, ballot) for ballot in deciphered_ballots.ballots]
    return verify(pk, evs, ballots, proof)