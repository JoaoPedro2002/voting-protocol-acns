# import env firt to load routes and tables
from env import port

import uvicorn
import os
from app import app

if __name__ == "__main__":
    kwargs = {
        "app": app,
        "port": port,
        "env_file": ".env" if os.path.exists(".env") else None
    }
    uvicorn.run(**kwargs)
