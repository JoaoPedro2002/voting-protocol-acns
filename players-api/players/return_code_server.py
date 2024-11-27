from app import app
from lbvs_lib.serializers import deserialize_ballot_proof, deserialize_encrypted_ballot, deserialize_pk, deserialize_vvk, deserialize_ck
from lbvs_lib.scheme_algorithms import code
from lbvs_lib.return_code_table import ReturnCodeTable

from classes import *


key = ReturnCodeTable.new_key()
keys = {}
voters_vvk_dict = {}


@app.post("/code/setup_keys")
async def setup(pk: ElectionPK, ck: ElectionCK, voters_vvk: dict[str, VoterVVK]):
    keys['pk'] = deserialize_pk(pk)
    keys['ck'] = deserialize_ck(ck)

    for voter_id, vvk in voters_vvk.items():
        voters_vvk_dict[voter_id] = deserialize_vvk(vvk)


def send_to_voter(code: str, vote: Vote) -> VoteConfirmation:
    # email code to voter
    # await confirmation
    # if confirmation:
    #    save ballot and proof
    # return confirmation {voter_id: voter_id, confirmation: confirmation}
    return VoteConfirmation(voter_id=vote.voter_id, confirmation=True)


@app.post("/code/casting")
async def casting_phase(vote: Vote) -> VoteConfirmation:
    ev = deserialize_encrypted_ballot(vote.ev)
    proof = deserialize_ballot_proof(vote.proof)
    precode = code(keys['pk'], keys['ck'], voters_vvk_dict[vote.voter_id], ev, proof)
    return send_to_voter(ReturnCodeTable.nmod_prf(key, precode, b64=True), vote)

@app.get("/code/send_to_auditor")
async def counting_phase() -> list[tuple[EncryptedBallot, BallotProof]]:
    # send all ballots to the auditor
    pass


