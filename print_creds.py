from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import User
import os

engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///./security_platform.db"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("==== CREDENTIALS ====")
for user in db.query(User).all():
    print(f"Username: {user.username} | Password: {user.password_hash} | Account: {getattr(user, 'account_number', 'N/A')}")
print("=====================")
