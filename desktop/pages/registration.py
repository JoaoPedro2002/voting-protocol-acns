import customtkinter as tk
from tkinter import messagebox
import requests

class RegistrationPage(tk.CTk):
    def __init__(self, json_file, session, username, back_page):
        super().__init__()

        self.back_page = back_page
        self.json_file = json_file
        self.username = username
        self.session = session

        self.election_url = json_file.data["election_url"]
        self.session = session

        self.title("Registration")
        self.geometry("400x250")

        self.main_frame = tk.CTkFrame(master=self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20)

        self.election_uuid = tk.CTkLabel(master=self.main_frame, text="Election UUID:")
        self.election_uuid.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.election_uuid_entry = tk.CTkEntry(master=self.main_frame)
        self.election_uuid_entry.grid(row=0, column=1, padx=10, pady=5)

        self.voter_phone = tk.CTkLabel(master=self.main_frame, text="Voter Phone:")
        self.voter_phone.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.voter_phone_entry = tk.CTkEntry(master=self.main_frame)
        self.voter_phone_entry.grid(row=1, column=1, padx=10, pady=5)

        # Register button
        self.register_button = tk.CTkButton(
            master=self.main_frame,
            text="Register",
            command=self.register_voter
        )
        self.register_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    def register_voter(self):
        election_uuid = self.election_uuid_entry.get()
        voter_phone = self.voter_phone_entry.get()

        url = self.election_url + "/helios/elections/" + election_uuid + "/register_lbvs"

        # Assuming election_uuid and election_url are accessible within this scope
        try:
            response = self.session.post(url, json={"voter_phone": voter_phone})
            response.raise_for_status()  # Raise an exception for bad status cod

            response_json = response.json()
            if "error" in response_json:
                raise requests.exceptions.RequestException(response_json["error"])

            del response_json['rct']
            response_json['election_uuid'] = election_uuid
            response_json['voter_phone'] = voter_phone
            self.json_file.data["voters"][self.username] = response_json
            self.json_file.save()

            messagebox.showinfo("Success", "Registration successful!")

            self.destroy()  # Close the registration window
            self.back_page(self.json_file, self.session, self.username).mainloop()

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Registration failed: {e}")