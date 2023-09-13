import base64
import hashlib
import time

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

"""
conda install -c conda-forge fastapi uvicorn python-multipart
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

SIGNIN_SECRET = "this-is-our-secret-key"

default_upload_ttl = 3 * 60  # 3 minutes


@app.get("/get-upload-information")
def get_upload_information(request: Request, filename: str):
    timestamp = int(time.time())

    # Let's use a proper library for creating this token
    payload = f"{default_upload_ttl}{filename}{timestamp}{SIGNIN_SECRET}"
    hash_value = hashlib.sha256(payload.encode()).hexdigest()

    app.state._document_cache[hash_value] = timestamp

    # Don't return timestamp here
    return {"upload_hash": hash_value, "timestamp": timestamp}


@app.post("/upload-document")
def upload_document(
    request: Request,
    upload_hash: str = Form(...),
    timestamp: int = Form(...),
    filename: str = Form(...),
    file: str = Form(...),
):
    timestamp = app.state._document_cache.get(upload_hash)
    if timestamp is None:
        raise Exception
    if timestamp - int(time.time()) > default_upload_ttl:
        raise Exception
    del app.state._document_cache[upload_hash]

    payload = f"{default_upload_ttl}{filename}{timestamp}{SIGNIN_SECRET}"
    computed_hash = hashlib.sha256(payload.encode()).hexdigest()

    if (
        computed_hash == upload_hash
        and timestamp - int(time.time()) < default_upload_ttl
    ):
        content_type, data = file.split(",")

        path = f"/tmp/{upload_hash}_{filename}"
        print(path)
        with open(path, "wb") as f:
            f.write(bytes(base64.b64decode(data)))

        return upload_hash
    else:
        raise HTTPException(status_code=400, detail="Invalid upload hash")


"""
fast api endpoint named upload-document that takes a signed hash and a file and stores the document under /tmp/{hash}
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
