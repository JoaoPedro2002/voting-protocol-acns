import requests
from lbvs_lib.compile import shared_library, MODP
from lbvs_lib.scheme_algorithms import count
from lbvs_lib.serializers2 import deserialize_encrypted_ballot, serialize_shuffle_proof, deserialize_pk, deserialize_dk, \
    recursive_serialize_nmod_poly
from lbvs_lib.shuffle import Shuffle

from app import app
from classes import *
from db.engine import SessionDep
from db.shuffle_server import ShuffleServerInstance


@app.post("/shuffler/setup")
def setup(setup_params: ShuffleServerSetup, session: SessionDep):
    instance = ShuffleServerInstance(dk=setup_params.dk.model_dump(mode='json'),
                                     **setup_params.instance.model_dump(mode='json'))
    session.add(instance)
    session.commit()

@app.post("/shuffler/counting")
def counting_phase(ballot_list: EncryptedBallotList, session: SessionDep):
    instance: ShuffleServerInstance = session.query(ShuffleServerInstance).filter_by(election_uuid=ballot_list.election_uuid).first()
    dk = deserialize_dk(instance.dk)
    evs = ballot_list.ballots
    proofs = []
    votes = []
    for evs_per_question in evs:
        dec_evs = []
        for ev in evs_per_question:
            dec_evs.append(deserialize_encrypted_ballot(ev))
        n_votes = len(dec_evs)
        votes_question, proof = count(dk, dec_evs)
        votes.append(recursive_serialize_nmod_poly(votes_question, [n_votes]))
        proofs.append(serialize_shuffle_proof(proof))

        y, _y, t, _t, u, d, s, rho = proof

        Shuffle.proof_clear(shared_library, y, _y, t, _t, u, d, s, rho, n_votes)
        # clear ballots
        # TODO
        for i in range(len(dec_evs)):
            shared_library.nmod_poly_clear(votes_question[i])

        # clear keys
        # TODO

    # send to the auditors
    proofs_and_ballots = {
        "shuffle_proof": proofs,
        "ballots": votes,
        "election_uuid": ballot_list.election_uuid
    }
    for auditor in instance.auditors_urls:
        requests.post(auditor + "/auditor/receive_shuffle_proof", json=proofs_and_ballots)

    return {"status": "success"}