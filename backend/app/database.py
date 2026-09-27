import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# When running in serverless cloud environments (like Vercel), the filesystem is read-only except /tmp
default_db = "sqlite:////tmp/smartbin.db" if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else "sqlite:///./smartbin.db"
DATABASE_URL = os.getenv("DATABASE_URL", default_db)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
