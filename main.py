from dotenv import load_dotenv

assert load_dotenv()

from ragna._cli import app


app(["launch"])
