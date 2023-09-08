from fastapi import FastAPI, UploadFile

from pydantic import BaseModel


class Input(BaseModel):
    prompt: str
    sources: list[str]


class Output(BaseModel):
    name: str
    price: float


app = FastAPI()


@app.post("/complete")
def complete(input: Input, output: Output):
    return input.json()


@app.get("/get-upload-info")
async def upload_document():
    return {"url": "", "fields": {}}


@app.post("/upload-document2")
async def upload_document2(file: UploadFile):
    return {"filename": file.filename}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
