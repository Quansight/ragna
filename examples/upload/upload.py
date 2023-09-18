import base64
import hashlib
import time
import secrets

from fastapi import FastAPI, Form, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

"""
conda install -c conda-forge fastapi uvicorn python-multipart "python-jose[cryptography]"

"""

import contextlib


@contextlib.contextmanager
def lifespan(app):
    app.state._document_cache = {}
    yield


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TODO: move to config, replace with another value, still 64 chars
SECRET_KEY = "89E2D768589AF14B9B89FA2CC4961A8C1685EE732FF2B0C88FD92A3BABD6D05E"

default_upload_ttl = 3 * 60  # 3 minutes


@app.get("/get-upload-information")
def get_upload_information(request: Request, filename: str):
    
    timestamp = int(time.time())

    to_encode = {"filename":filename, "timestamp":timestamp}

    hash = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

    # Don't return timestamp here
    return {"upload_hash": hash}


@app.post("/upload-document")
def upload_document(
    request: Request,
    upload_hash: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
):

    try:
        payload = jwt.decode(upload_hash, SECRET_KEY, algorithms=["HS256"])
        
        if int(time.time()) - payload['timestamp']  > default_upload_ttl:
            raise HTTPException(status_code=400, detail="Expired upload hash")    

        if payload['filename'] != filename:
            raise HTTPException(status_code=400, detail="Invalid upload hash")

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid upload hash")
    except NameError:
        # raised in case the payload is invalid
        raise HTTPException(status_code=400, detail="Invalid upload hash")


    # at this point, the hash and the timestamp are valid, 
    # let's proceed to the upload of the file

    path = f"/tmp/{payload['timestamp']}_{filename}"

    with open(path, 'wb') as f:
        while data := file.file.read(1024 * 1024):
            f.write(data)



    return upload_hash



"""
fast api endpoint named upload-document that takes a signed hash and a file and stores the document under /tmp/{hash}
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
