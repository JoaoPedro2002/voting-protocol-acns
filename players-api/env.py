import os

port = int(os.environ.get("PORT", "8080"))

# Load only required modules
modules = ["SHUFFLE_SERVER", "RETURN_CODE_SERVER", "AUDITOR", "VOTER"]
for module in modules:
    if os.environ.get(module):
        exec(f"from db.{module.lower()} import *")
        exec(f"from players.{module.lower()} import *")