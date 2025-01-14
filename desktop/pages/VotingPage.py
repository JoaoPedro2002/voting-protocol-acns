from tkinter.constants import VERTICAL

import customtkinter as tk
from tkinter import messagebox, Scrollbar
from lbvs_lib.serializers2 import deserialize_vck, deserialize_pk, serialize_encrypted_ballot, serialize_ballot_proof
from lbvs_lib.scheme_algorithms import cast as libcast
from lbvs_lib.compile import shared_library, MODP
from lbvs_lib.classes import NMOD_POLY_TYPE
from lbvs_lib.cleanup import clear_ev_and_proof, clear_voter
import requests

class VotingPage(tk.CTk):
    def __init__(self, json_file, session, username):
        super().__init__()

        self.json_file = json_file
        self.session = session
        self.voter = json_file.data["voters"][username]
        self.election_uuid = self.voter["election_uuid"]
        self.election_url = json_file.data["election_url"]
        self.election = self.get_election()
        self.election_instance = self.get_election_instance()

        self.title("Voting Page for " + self.election["name"])
        self.geometry("500x400")

        self.main_frame = tk.CTkFrame(master=self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20)

        self.canvas = tk.CTkCanvas(master=self.main_frame)
        self.canvas.grid(row=0, column=0, sticky="news")

        self.scrollbar = Scrollbar(master=self.main_frame, orient=VERTICAL, command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.config(yscrollcommand = self.scrollbar.set)

        self.inner_frame = tk.CTkFrame(master=self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.answers = []

        # Create a frame for each question
        self.vars = []
        for i, question in enumerate(self.election["questions"]):
            question_frame = tk.CTkFrame(master=self.inner_frame)
            question_frame.grid(row=i, column=0, padx=10, pady=10, sticky="w")

            question_label = tk.CTkLabel(master=question_frame, text=f"Question {i+1}: {question['question']}")
            question_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

            min_max_text = f"Select between {question.get('min', 1)} and {question.get('max', len(question['answers']))} answers"
            min_max_label = tk.CTkLabel(master=question_frame,
                                        text=min_max_text)
            min_max_label.grid(row=1, column=0, padx=5, pady=5)

            # Create checkboxes for each option

            _vars = []
            for j, option in enumerate(question['answers']):
                var = tk.BooleanVar()
                _vars.append(var)
                option_checkbox = tk.CTkCheckBox(master=question_frame, text=option, variable=var)
                option_checkbox.grid(row=j+2, column=0, padx=5, pady=2)
            self.vars.append(_vars)

        # Create a submit button
        self.submit_button = tk.CTkButton(
            master=self.main_frame,
            text="Submit Vote",
            command=self.submit_vote
        )
        self.submit_button.grid(row=len(self.election["questions"]) + 1, column=0, padx=10, pady=10)

    def submit_vote(self):
        # Validate answers
        if not self.validate_answers():
            messagebox.showerror("Error", "Invalid number of answers selected.")
            return

        # Collect selected answers
        self.answers = []
        for i, question in enumerate(self.election["questions"]):
            selected_options = []
            for j, var in enumerate(self.vars[i]):
                if var.get():
                    selected_options.append(j)
            self.answers.append(selected_options)

        vck = deserialize_vck(self.voter["vck"])
        pk = deserialize_pk(self.election_instance["pk"])

        returnable = {
            "voter_uuid": self.voter["voter_uuid"],
            "election_uuid": self.election_uuid,
            "questions": []
        }

        poly = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(poly, MODP)
        for answer in self.answers:
            for choice in answer:
                shared_library.nmod_poly_set_coeff_ui(poly, choice, 1)
            ev, pv = libcast(pk, vck, poly)
            ev_ser = serialize_encrypted_ballot(ev)
            pv_ser = serialize_ballot_proof(pv)
            clear_ev_and_proof(ev, pv)
            returnable["questions"].append({"ev": ev_ser, "proof": pv_ser})

            shared_library.nmod_poly_zero(poly)
        shared_library.nmod_poly_clear(poly)
        clear_voter((None, vck, None))

        # send vote to phone so it knows the return code to expect
        self.session.post(self.voter["voter_phone"] + "/phone/expected_return_codes", json={
            "voter_uuid": self.voter["voter_uuid"],
            "vote": {"questions": self.answers},
            # not used in the phone
            "username": "anything",
            "password": "anything"
        })

        # Send vote data to server
        resp = self.session.post(f"{self.election_url}/helios/elections/{self.election_uuid}/cast_confirm", json=returnable)

        if resp.status_code == 200:
            messagebox.showinfo("Success", "Vote submitted successfully!")
            self.destroy()
        else:
            messagebox.showerror("Error", "Vote submission failed.")

    def validate_answers(self):
        for i, question in enumerate(self.election["questions"]):
            var = self.vars[i]
            selected_count = sum([v.get() for v in var])
            if (selected_count < question.get('min', 1)
                    or selected_count > question.get('max', len(question['answers']))):
                return False
        return True

    def get_election(self):
        url = self.election_url + "/helios/elections/" + self.election_uuid
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_election_instance(self):
        url = self.election_url + "/helios/elections/" + self.election_uuid + "/lbvs_instance"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()