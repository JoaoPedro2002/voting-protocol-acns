from requests import session

from app import app
from lbvs_lib.serializers import deserialize_ballot_proof, deserialize_encrypted_ballot, deserialize_pk, deserialize_vvk, deserialize_ck
from lbvs_lib.scheme_algorithms import code
from lbvs_lib.return_code_table import ReturnCodeTable

from classes import *

import base64

from db.return_code_server import ReturnCodeServerInstance
from db.common import Vote as VoteDB, VoterPublicData, Question as QuestionDB
from db.engine import SessionDep


@app.post("/code/setup")
async def setup(setup_params: ReturnCodeSetup, session: SessionDep) -> PrfKey:
    key = base64.b64encode(ReturnCodeTable.new_key()).decode('utf-8')

    instance = ReturnCodeServerInstance(ck=setup_params.ck,
                                        prf_key=key,
                                        **setup_params.model_dump(mode='json'))
    session.add(instance)
    session.commit()

    return PrfKey(key=key)

@app.get("/code/key")
async def get_key(election_uuid, session: SessionDep) -> PrfKey:
    instance = get_instance(election_uuid, session)
    return PrfKey(key=instance.prf_key)

@app.post("/code/register")
async def register(voter: VoterRegistration, session: SessionDep):
    voter_data = VoterPublicData(voter_uuid=voter.voter_uuid,
                                 voter_email=voter.voter_email,
                                 election_uuid=voter.election_uuid,
                                 vvk=voter.vvk)
    session.add(voter_data)
    session.commit()


@app.post("/code/casting")
async def casting_phase(vote: Vote, session: SessionDep) -> VoteConfirmation:
    instance = get_instance(vote.election_uuid, session)
    prf_key_bytes = base64.b64decode(instance.prf_key)
    voter_data: VoterPublicData = session.query(VoterPublicData).filter_by(voter_uuid=vote.voter_uuid).first()
    pk = deserialize_pk(instance.pk)
    ck = deserialize_ck(instance.ck)

    return_codes = []
    for question in vote.questions:
        ev = deserialize_encrypted_ballot(question.ev)
        proof = deserialize_ballot_proof(question.proof)
        vvk = deserialize_vvk(voter_data.vvk)
        precode = code(pk, ck, vvk, ev, proof)
        return_code = ReturnCodeTable.nmod_prf(prf_key_bytes, precode, b64=True)
        return_codes.append(return_code)

    return send_to_voter(return_codes, voter_data)


def send_to_voter(return_codes: list[str], voter_data: VoterPublicData,
                  vote: Vote, session: SessionDep) -> VoteConfirmation:
    # email code to voter
    # await confirmation
    confirmation = True
    # if confirmation:
    #    save ballot and proof
    if confirmation:
        vote_db = VoteDB(voter_id=voter_data.voter_uuid, election_uuid=vote.election_uuid)
        questions = [QuestionDB(ev=question.ev, proof=question.proof, vote=vote_db) for question in vote.questions]
        session.add(vote_db)
        session.add_all(questions)
        session.commit()
    # return confirmation {voter_id: voter_id, confirmation: confirmation}
    return VoteConfirmation(voter_id=voter_data.voter_uuid, confirmation=confirmation)


@app.get("/code/send_to_auditor")
async def counting_phase(election_uuid: str, session: SessionDep) -> list[list[tuple[EncryptedBallot, BallotProof]]]:
    # send all ballots to the auditor
    votes = session.query(VoteDB).filter_by(election_uuid=election_uuid).all()
    ballots = [[(question.ev, question.proof) for question in vote.questions] for vote in votes]
    return ballots


def get_instance(election_uuid: str, session: SessionDep) -> ReturnCodeServerInstance:
    return session.query(ReturnCodeServerInstance).filter_by(election_uuid=election_uuid).first()



