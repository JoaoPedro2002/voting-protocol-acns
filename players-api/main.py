import uvicorn

from app import app

import os


port = int(os.environ.get("PORT", "8000"))

# Load only required modules
modules = ["SHUFFLE_SERVER", "RETURN_CODE_SERVER", "AUDITOR"]
for module in modules:
    if os.environ.get(module):
        exec(f"from players.{module.lower()} import *")

if __name__ == "__main__":
    kwargs = {
        "app": app,
        "port": port,
        "env_file": ".env" if os.path.exists(".env") else None
    }
    uvicorn.run(**kwargs)
