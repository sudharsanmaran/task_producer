from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
load_dotenv()
import os

Base = declarative_base()

username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")
sslmode = "require"
port = os.getenv("DB_PORT")

# flake8: noqa
# database_url = f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}?sslmode={sslmode}"
database_url = f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"

engine = create_engine(database_url, pool_size=5, max_overflow=0)
ScopedSession = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db() -> scoped_session:
    global database_url

    session = ScopedSession()
    try:
        yield session
    finally:
        session.close()
