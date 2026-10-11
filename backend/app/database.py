import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv("../.env")

DATABASE_URL = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@localhost:"
    f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine)