import requests
import sys
import random
import time

ALL_USERS = ["riemann", "gauss", "euler", "euclid", "einstein", "newton", "galieleo", "tesla"]

if __name__ == "__main__":
    voter_url = sys.argv[1]
    election_url = sys.argv[2]
    election_uuid = sys.argv[3]
    voter_phone = sys.argv[4]
    election_pass = sys.argv[5]

    if len(sys.argv) > 6:
        election_users = sys.argv[6].split(",")
    else:
        election_users = ALL_USERS

    election_resp = requests.get(election_url + "/helios/elections/" + election_uuid)
    election_resp.raise_for_status()
    election_json = election_resp.json()

    remaining_voters = election_users.copy()

    try:

        for user in election_users:
            print(f"Registering {user}...")
            response = requests.post(
                voter_url + "/voter/register",
                json={
                    "url": election_url,
                    "election_uuid": election_uuid,
                    "user": user,
                    "password": election_pass,
                    "voter_phone": voter_phone
                })
            response.raise_for_status()
            resp_json = response.json()

            remaining_voters.remove(user)
            if "error" in resp_json:
                print(f"Error: {resp_json['error']}")
                continue

            voter_uuid = resp_json["voter_uuid"]

            print(f"Registered {user} successfully. UUID: {voter_uuid}")

            answers = []
            for question in election_json["questions"]:
                max_ans = question["max"]
                min_ans = question["min"]
                len_ans = len(question["answers"])
                answ_ind = []
                for i in range(len_ans):
                    answ_ind.append(i)
                ans_n = random.randint(min_ans, max_ans)
                answers.append(random.sample(answ_ind, ans_n))

            print(f"{user} plain vote: {answers}")
            response = requests.post(
                voter_url + "/voter/cast_to_helios",
                json={
                    "voter_uuid": voter_uuid,
                    "username": user,
                    "password": election_pass,
                    "vote": {
                        "questions": answers
                    }
                })
            response.raise_for_status()
            print(f"Vote for {user} cast successfully.")
            # not overload the ldap server
            time.sleep(2)
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        print("Check if the ldap server is down and try again.")
        print(f"Remaining users: {remaining_voters}")
        sys.exit(1)