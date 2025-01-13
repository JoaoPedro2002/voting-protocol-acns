import requests
from lbvs_lib.compile import shared_library, MODP
from lbvs_lib.classes import NMOD_POLY_TYPE
from lbvs_lib.cleanup import clear_ev_and_proof
from lbvs_lib.serializers2 import deserialize_shuffle_proof, deserialize_nmod_poly, deserialize_encrypted_ballot, \
    recursive_deserialize_nmod_poly, deserialize_pk, serialize_nmod_poly, deserialize_ballot_proof
from lbvs_lib.primitives import vericrypt
from lbvs_lib.scheme_algorithms import verify
from lbvs_lib.utils import ev_equals, pv_equals
from requests import session

from app import app, SessionDep
from classes import DecipheredBallots, AuditorSetup, EncryptedBallotProofList
from db.auditor import AuditorInstance


@app.post("/auditor/setup")
def setup(setup_params: AuditorSetup, session: SessionDep):
    instance = AuditorInstance(**setup_params.instance.model_dump(mode='json'))
    session.add(instance)
    session.commit()

@app.post("/auditor/verify_ballots")
def verify_ballots(ev_and_proof_from_bb: EncryptedBallotProofList, session: SessionDep) -> dict:
    election_uuid = ev_and_proof_from_bb.election_uuid
    instance: AuditorInstance = session.query(AuditorInstance).filter_by(election_uuid=election_uuid).first()
    request_to_rcs = requests.get(instance.return_code_server_url + "/code/send_to_auditor",
                                  params={"election_uuid": election_uuid})
    ev_and_proof_from_rcs = EncryptedBallotProofList(**request_to_rcs.json())

    bb_ballots_proofs = ev_and_proof_from_bb.ballots_and_proofs
    rcs_ballots_proofs = ev_and_proof_from_rcs.ballots_and_proofs

    assert len(bb_ballots_proofs) == len(rcs_ballots_proofs)

    equal_ballots = True

    evs_to_save = []
    proofs_to_save = []

    for i in range(len(bb_ballots_proofs)):
        evs_question = []
        proofs_question = []
        evs_to_save.append(evs_question)
        proofs_to_save.append(proofs_question)
        for j in range(len(bb_ballots_proofs[i])):
            ev_bb, proof_bb = bb_ballots_proofs[i][j].ev, bb_ballots_proofs[i][j].proof
            ev_rcs, proof_rcs = rcs_ballots_proofs[i][j].ev, rcs_ballots_proofs[i][j].proof

            evs_question.append(ev_bb)
            proofs_question.append(proof_bb)

            ev_ballot_box = deserialize_encrypted_ballot(ev_bb)
            proof_ballot_box = deserialize_ballot_proof(proof_bb)

            ev_code_server = deserialize_encrypted_ballot(ev_rcs)
            proof_code_server = deserialize_ballot_proof(proof_rcs)

            if not ev_equals(shared_library, ev_ballot_box, ev_code_server, vericrypt.context):
                equal_ballots = False
            if not pv_equals(shared_library, proof_ballot_box, proof_code_server, vericrypt.context):
                equal_ballots = False

            clear_ev_and_proof(ev_ballot_box, proof_ballot_box)
            clear_ev_and_proof(ev_code_server, proof_code_server)

            if not equal_ballots:
                break

    instance.evs = evs_to_save
    instance.proofs = proofs_to_save

    session.add(instance)
    session.commit()

    return {"equal_ballots": equal_ballots}


@app.post("/auditor/receive_shuffle_proof")
def receive_shuffle_proof(deciphered_ballots: DecipheredBallots, session: SessionDep):
    instance: AuditorInstance = session.query(AuditorInstance).filter_by(election_uuid=deciphered_ballots.election_uuid).first()
    instance.shuffle_proofs = deciphered_ballots.shuffle_proof
    instance.ballots = deciphered_ballots.ballots
    session.add(instance)
    session.commit()

@app.get("/auditor/ready")
def ready(election_uuid: str, session: SessionDep) -> dict[str, bool]:
    instance = session.query(AuditorInstance).filter_by(election_uuid=election_uuid).first()
    ready = instance.shuffle_proofs is not None and instance.ballots is not None
    return {
        "ready": ready
    }


@app.get("/auditor/verify_shuffle")
def counting_phase(election_uuid: str,session: SessionDep) -> dict:
    instance = session.query(AuditorInstance).filter_by(election_uuid=election_uuid).first()
    pk = deserialize_pk(instance.pk)

    result = True
    election_count = []
    election_ballots = []
    for i in range(len(instance.shuffle_proofs)):
        proof = deserialize_shuffle_proof(instance.shuffle_proofs[i])
        n_votes = len(instance.ballots[i])
        ballots = (NMOD_POLY_TYPE * n_votes)()
        recursive_deserialize_nmod_poly(ballots, instance.ballots[i], [n_votes])
        evs = [deserialize_encrypted_ballot(ev) for ev in instance.evs[i]]
        result &= verify(pk, evs, ballots, proof)

        aux = NMOD_POLY_TYPE()
        aux2 = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(aux, MODP)
        shared_library.nmod_poly_init(aux2, MODP)
        shared_library.nmod_poly_zero(aux2)
        election_ballots.append([])
        for j in range(n_votes):
            shared_library.nmod_poly_add(aux, ballots[j], proof[7])
            shared_library.nmod_poly_add(aux2, aux2, aux)
            election_ballots[i].append(serialize_nmod_poly(aux))
            shared_library.nmod_poly_clear(ballots[j])
        election_count.append(serialize_nmod_poly(aux2))
        shared_library.nmod_poly_clear(aux)
        shared_library.nmod_poly_clear(aux2)

    return {
        "result": result,
        "election_count": election_count,
        "ballots": election_ballots
    }