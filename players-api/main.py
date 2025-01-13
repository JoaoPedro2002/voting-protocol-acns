# import env firt to load routes and tables
from env import port
from lbvs_lib.serializers2 import set_repr

import uvicorn
import os
from app import app

if __name__ == "__main__":
    set_repr("str")
    kwargs = {
        "app": app,
        "port": port,
        "env_file": ".env" if os.path.exists(".env") else None
    }
    uvicorn.run(**kwargs)
