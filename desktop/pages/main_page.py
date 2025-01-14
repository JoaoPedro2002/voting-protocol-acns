import customtkinter as tk

from pages.VotingPage import VotingPage
from pages.registration import RegistrationPage


class MainPage(tk.CTk):
    def __init__(self, json_file, session, username):
        super().__init__()

        self.title("Voting System")
        self.geometry("250x150")

        self.json_file = json_file
        self.session = session

        self.main_frame = tk.CTkFrame(master=self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20)

        # Create buttons within the frame
        voters = json_file.data["voters"]
        if not username in voters:
            self.register_button = tk.CTkButton(
                master=self.main_frame,
                text="Register",
                command=lambda: self.open_registration_page(username)
            )
            self.register_button.grid(row=0, column=0, padx=10, pady=10)
        else:
            self.vote_button = tk.CTkButton(
                master=self.main_frame,
                text="Vote",
                command=lambda: self.open_voting_page(username)
            )
            self.vote_button.grid(row=1, column=0, padx=10, pady=10)

    def open_registration_page(self, username):
        registration_page = RegistrationPage(self.json_file, self.session, username, self.__class__)
        self.destroy()
        registration_page.mainloop()

    def open_voting_page(self, username):
        voting_page = VotingPage(self.json_file, self.session, username)
        self.destroy()
        voting_page.mainloop()


