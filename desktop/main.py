import customtkinter as ctk
from lbvs_lib.serializers2 import set_repr

from json_file import JsonFile
from pages.login import LoginPage

# Selecting GUI theme - dark, light , system (for system default)
ctk.set_appearance_mode("dark")

# Selecting color theme - blue, green, dark-blue
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    set_repr("str")
    json_file_path = "stored_json.json"
    json_file = JsonFile(json_file_path)
    app = LoginPage(json_file)
    app.mainloop()
