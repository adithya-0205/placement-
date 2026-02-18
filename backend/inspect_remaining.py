from database import SessionLocal
from sqlalchemy import text

def inspect_remaining():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, explanation FROM questions WHERE branch='MECH' AND LENGTH(TRIM(correct_answer)) != 1"))
        rows = res.fetchall()
        print(f"--- Remaining {len(rows)} Malformed MECH Questions ---")
        for r in rows:
            print(f"ID: {r[0]}")
            print(f"Q: {r[1][:50]}...")
            print(f"A: {r[2]} | B: {r[3]} | C: {r[4]} | D: {r[5]}")
            print(f"ANS: '{r[6]}'")
            print(f"EXP: {r[7][:100]}...")
            print("-" * 30)
    finally:
        db.close()

if __name__ == '__main__':
    inspect_remaining()
