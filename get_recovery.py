from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import User
import json
import os

engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///./security_platform.db"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("==== RECOVERY CARDS ====")
for user in db.query(User).all():
    print(f"User: {user.username}")
    if user.recovery_card_data:
        try:
            card = json.loads(user.recovery_card_data)
            print("Card Grid:")
            for row in range(1, 7):
                row_str = f"Row {row}: "
                for col in "ABCDEF":
                    key = f"{col}{row}"
                    val = card.get(key, ' ')
                    row_str += f"{key}={val} "
                print(row_str)
        except Exception as e:
            print("Could not parse card:", e)
    else:
        print("No card data.")
    print("-" * 20)
