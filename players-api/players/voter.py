from app import app
from classes import *
import requests

@app.post("/voter/register")
def register(url: str, election_uuid: str, user: str, password: str):
    s = requests.Session()
    login_url = url + "/auth/ldap/login"
    login_data = {"username": user, "password": password}
    res = s.post(login_url, data=login_data)

    election_url = url + "/helios/elections/" + election_uuid
    instance = ElectionInstance(**s.get(election_url + "/lbvs_instance").json())
    params = s.post(election_url + "/register_lbvs", json=instance.dict())
    print(instance.model_dump(mode="json"))

@app.post("/voter/cast")
def cast():
    pass