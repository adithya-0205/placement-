from database import SessionLocal
from sqlalchemy import text

def list_users():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT username FROM users LIMIT 5"))
        print("Users:", [r[0] for r in res])
    finally:
        db.close()

if __name__ == '__main__':
    list_users()
