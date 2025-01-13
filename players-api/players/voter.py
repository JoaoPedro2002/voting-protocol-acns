import json

from app import app
from classes import *
import requests

from db.engine import SessionDep
from db.voter import VoterInstance

from lbvs_lib.serializers2 import deserialize_vck, deserialize_pk, serialize_encrypted_ballot, serialize_ballot_proof
from lbvs_lib.scheme_algorithms import cast as libcast
from lbvs_lib.compile import shared_library, MODP
from lbvs_lib.classes import NMOD_POLY_TYPE
from lbvs_lib.cleanup import clear_ev_and_proof, clear_voter


def login_ldap_helios(url: str, user: str, password: str):
    s = requests.Session()
    login_url = url + "/auth/ldap/login"
    login_data = {"username": user, "password": password}
    s.post(login_url, data=login_data)
    return s

@app.post("/voter/register")
def register(url: str, election_uuid: str, user: str, password: str, voter_phone: str,
             session: SessionDep):
    s = login_ldap_helios(url, user, password)

    election_url = url + "/helios/elections/" + election_uuid
    instance = ElectionInstance(**s.get(election_url + "/lbvs_instance").json())
    params = s.post(election_url + "/register_lbvs", json={"voter_phone": voter_phone}).json()

    session.add(VoterInstance(vvk=params["vvk"],vck=params["vck"], voter_uuid=params["voter_uuid"], voter_phone=voter_phone,
                              **instance.model_dump(mode="json")))

    session.commit()

    return {"voter_uuid": params["voter_uuid"]}

def cast(instance: VoterInstance, votes: list[list[int]]) -> Vote:
    vck = deserialize_vck(instance.vck)
    pk = deserialize_pk(instance.pk)

    returnable = Vote(voter_uuid=instance.voter_uuid, election_uuid=instance.election_uuid, questions=[])

    poly = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(poly, MODP)
    for vote in votes:
        for choice in vote:
            shared_library.nmod_poly_set_coeff_ui(poly, choice, 1)
        ev, pv = libcast(pk, vck, poly)
        ev_ser = serialize_encrypted_ballot(ev)
        pv_ser = serialize_ballot_proof(pv)
        clear_ev_and_proof(ev, pv)
        returnable.questions.append(Question(ev=ev_ser, proof=pv_ser))

        shared_library.nmod_poly_zero(poly)

    shared_library.nmod_poly_clear(poly)
    clear_voter((None, vck, None))

    return returnable

@app.post("/voter/cast_to_helios")
def cast_to_helios(tbcast: TBCastVote, session: SessionDep) -> VoteConfirmation:
    instance: VoterInstance = session.query(VoterInstance).filter(VoterInstance.voter_uuid == tbcast.voter_uuid).first()
    s = login_ldap_helios(instance.ballot_box_url, tbcast.username, tbcast.password)
    vote = cast(instance, tbcast.vote.questions)
    # send vote to phone so it knows the return code to expect
    requests.post(instance.voter_phone + "/phone/expected_return_codes", json=tbcast.model_dump(mode="json"))

    # add encrypted vote to session
    s.post(f"{instance.election_url}/cast_confirm", json=vote.model_dump(mode="json"))


    # send vote to helios
    # confirmation = requests.post(f"{instance.election_url}/cast_pqc", json=vote.model_dump(mode="json"))

    # return VoteConfirmation(**confirmation.json())
    return VoteConfirmation(voter_uuid=tbcast.voter_uuid, confirmation=True)