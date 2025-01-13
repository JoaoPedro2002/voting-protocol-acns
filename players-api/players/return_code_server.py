import requests
from sqlalchemy import func

from app import app
from lbvs_lib.serializers2 import deserialize_ballot_proof, deserialize_encrypted_ballot, deserialize_pk, deserialize_vvk, deserialize_ck
from lbvs_lib.scheme_algorithms import code
from lbvs_lib.return_code_table import ReturnCodeTable

from classes import *

import base64

from db.return_code_server import ReturnCodeServerInstance
from db.common import Vote as VoteDB, VoterPublicData, Question as QuestionDB
from db.engine import SessionDep


@app.post("/code/setup")
async def setup(setup_params: ReturnCodeSetup, session: SessionDep):
    key = ReturnCodeTable.new_key()
    b64key = ReturnCodeTable.encode_key(key)

    instance = ReturnCodeServerInstance(ck=setup_params.ck.model_dump(mode='json'),
                                        prf_key=b64key,
                                        **setup_params.instance.model_dump(mode='json'))
    session.add(instance)
    session.commit()

@app.get("/code/key")
async def get_key(election_uuid, session: SessionDep) -> PrfKey:
    instance = get_instance(election_uuid, session)
    return PrfKey(key=instance.prf_key)

@app.post("/code/register")
async def register(voter: VoterRegistration, session: SessionDep):
    voter_data = VoterPublicData(voter_uuid=voter.voter_uuid,
                                 voter_phone_address=voter.voter_phone_address,
                                 election_uuid=voter.election_uuid,
                                 vvk=voter.vvk.model_dump(mode='json'))
    session.add(voter_data)
    session.commit()


@app.post("/code/casting")
async def casting_phase(vote: Vote, session: SessionDep) -> VoteConfirmation:
    instance = get_instance(vote.election_uuid, session)
    prf_key_bytes = base64.b64decode(instance.prf_key)
    voter_data: VoterPublicData = session.query(VoterPublicData).filter_by(voter_uuid=vote.voter_uuid).first()
    pk = deserialize_pk(instance.pk)
    ck = deserialize_ck(instance.ck)
    vvk = deserialize_vvk(voter_data.vvk)

    return_codes = []
    for question in vote.questions:
        ev = deserialize_encrypted_ballot(question.ev)
        proof = deserialize_ballot_proof(question.proof)
        precode, result = code(pk, ck, vvk, ev, proof)
        return_code = ReturnCodeTable.nmod_prf(prf_key_bytes, precode, b64=True)
        return_codes.append(return_code)

    # clear keys
    return send_to_voter(return_codes, voter_data, vote, session)


def send_to_voter(return_codes: list[str], voter_data: VoterPublicData,
                  vote: Vote, session: SessionDep) -> VoteConfirmation:
    # send return codes to voter phone
    phone_resp = requests.post(voter_data.voter_phone_address + "/phone/verify", json={
        "voter_uuid": voter_data.voter_uuid,
        "return_codes": [{"code": ret_code} for ret_code in return_codes]
    }).json()
    vote_confirmation = VoteConfirmation(**phone_resp)

    if vote_confirmation.confirmation:
        vote_db = VoteDB(voter_id=voter_data.voter_uuid, election_uuid=vote.election_uuid)
        questions = [QuestionDB(ev=question.ev, proof=question.proof, vote=vote_db) for question in vote.questions]
        session.add(vote_db)
        session.add_all(questions)
        session.commit()

    return vote_confirmation


@app.get("/code/send_to_auditor")
async def counting_phase(election_uuid: str, session: SessionDep) -> EncryptedBallotProofList:
    # send all ballots to the auditor. Only consider the newest ballots
    votes = session.query(VoteDB, func.max(VoteDB.created_at)).\
            filter_by(election_uuid=election_uuid).\
            group_by(VoteDB.voter_id).order_by(VoteDB.created_at.desc()).all()
    ballots = []
    for vote, _ in votes:
        for i in range(len(vote.questions)):
            ev = vote.questions[i].ev
            proof = vote.questions[i].proof
            if len(ballots) <= i:
                ballots.append([])
            ballots[i].append(EncryptedBallotProof(ev=ev, proof=proof))

    return EncryptedBallotProofList(ballots_and_proofs=ballots, election_uuid=election_uuid)


def get_instance(election_uuid: str, session: SessionDep) -> ReturnCodeServerInstance:
    return session.query(ReturnCodeServerInstance).filter_by(election_uuid=election_uuid).first()



