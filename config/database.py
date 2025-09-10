import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC")

# Synchronous engine and session
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,  # Increase the pool size
    max_overflow=20,  # Increase the overflow limit
    pool_timeout=30,  # Timeout in seconds
)

Session = sessionmaker(bind=engine)

# Asynchronous engine and session
engine_async = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=True,  # Enable SQL statement logging
)

AsyncSessionLocal = sessionmaker(
    bind=engine_async,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency for synchronous sessions
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

# Dependency for asynchronous sessions
async def get_async_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

# Base declarative class for ORM models
Base = declarative_base()
