from fastapi import FastAPI
from pydantic import BaseModel


class Input(BaseModel):
    prompt: str
    sources: list[str]


app = FastAPI()


@app.post("/complete")
def complete(input: Input):
    return input.json()
