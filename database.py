from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = "sqlite:///./todosapp.db"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


## mssql+pyodbc://localhost/DummyDataDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes