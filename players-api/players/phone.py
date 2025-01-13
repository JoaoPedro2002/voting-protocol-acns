from app import app
from classes import *
from lbvs_lib.compile import shared_library, MODP
from lbvs_lib.classes import NMOD_POLY_TYPE
from lbvs_lib.return_code_table import ReturnCodeTable

from db.engine import SessionDep
from db.phone import PhoneInstance


@app.post("/phone/register")
def register(registration: PhoneRegistration, session: SessionDep):
    instance = PhoneInstance(**registration.model_dump(mode='json'), expected_return_codes=[])
    session.add(instance)
    session.commit()


@app.post("/phone/expected_return_codes")
def expected_return_codes(tbcast: TBCastVote, session: SessionDep):
    voter_uuid = tbcast.voter_uuid
    votes = tbcast.vote.questions

    phone_instance: PhoneInstance = session.query(PhoneInstance).filter(PhoneInstance.voter_uuid == voter_uuid).first()

    poly = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(poly, MODP)
    return_codes = []
    for i, question in enumerate(votes):
        for choice in question:
            shared_library.nmod_poly_set_coeff_ui(poly, choice, 1)
        s = ReturnCodeTable.nmod_table_key(poly, True)
        return_codes.append(phone_instance.rct[i][s])
        shared_library.nmod_poly_zero(poly)
    shared_library.nmod_poly_clear(poly)

    phone_instance.expected_return_codes = return_codes
    session.add(phone_instance)
    session.commit()


@app.post("/phone/verify")
def verify(phone_verification: PhoneVerification, session: SessionDep) -> VoteConfirmation:
    voter_uuid = phone_verification.voter_uuid
    phone_instance: PhoneInstance = session.query(PhoneInstance).filter(PhoneInstance.voter_uuid == voter_uuid).first()

    assert len(phone_verification.return_codes) == len(phone_instance.expected_return_codes)

    confirmation = True
    # TODO
    # for i in range(len(phone_verification.return_codes)):
    #     confirmation &= phone_verification.return_codes[i].code == phone_instance.expected_return_codes[i]

    return VoteConfirmation(voter_uuid=voter_uuid, confirmation=confirmation)