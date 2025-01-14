import customtkinter as tk
from tkinter import messagebox
import requests

from pages.main_page import MainPage

login_page = None
election_url_entry = None
user_entry = None
user_pass = None

s = requests.Session()

class LoginPage(tk.CTk):
    def __init__(self, json_file):
        super().__init__()

        self.json_file = json_file

        self.main_frame = tk.CTkFrame(master=self)
        self.main_frame.grid(row=0, column=0, padx=70, pady=20)

        self.title("Login")
        self.geometry("400x200")

        self.election_url_label = tk.CTkLabel(master=self.main_frame, text="Election URL:")
        self.election_url_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.election_url_entry = tk.CTkEntry(master=self.main_frame)
        self.election_url_entry.grid(row=0, column=1, padx=10, pady=5)

        if "election_url" in self.json_file.data:
            self.election_url_entry.insert(0, self.json_file.data["election_url"])

        self.username_label = tk.CTkLabel(master=self.main_frame, text="Username:")
        self.username_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.username_entry = tk.CTkEntry(master=self.main_frame)
        self.username_entry.grid(row=1, column=1, padx=10, pady=5)

        self.password_label = tk.CTkLabel(master=self.main_frame, text="Password:")
        self.password_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = tk.CTkEntry(master=self.main_frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=10, pady=5)

        self.login_button = tk.CTkButton(
                master=self,
                text="Login",
                command=self.login
            )
        self.login_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def login(self):
        election_url = self.election_url_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()

        try:
            response = login_ldap_helios(s, election_url, username, password)
            response.raise_for_status()
            if response.url == f"{election_url}/auth/ldap/login":
                raise requests.exceptions.RequestException("Invalid credentials")

            # Successful login, open main page
            self.json_file.data["election_url"] = election_url
            self.json_file.save()
            self.destroy()
            MainPage(self.json_file, s, username).mainloop()

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Login failed: {e}")


def login_ldap_helios(s, url: str, user: str, password: str):
    login_url = url + "/auth/ldap/login"
    login_data = {"username": user, "password": password}
    return s.post(login_url, data=login_data)

