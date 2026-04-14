from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ea.settings import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
