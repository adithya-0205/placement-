from database import SessionLocal
from sqlalchemy import text

def inspect_eee():
    db = SessionLocal()
    try:
        # Find any MECH question where correct_answer isn't just A,B,C,D,E
        print("--- Auditing MECH Answer Format ---")
        query = text("""
            SELECT id, correct_answer FROM questions 
            WHERE branch='MECH' 
            AND LENGTH(TRIM(correct_answer)) > 1
        """)
        res = db.execute(query)
        rows = res.fetchall()
        print(f"Found {len(rows)} MECH questions with malformed answers.")
        for row in rows:
            print(f"ID {row[0]}: '{row[1]}'")
            
        # Also check for lowercase
        print("\n--- Checking for lowercase MECH answers ---")
        query_lc = text("SELECT id, correct_answer FROM questions WHERE branch='MECH' AND correct_answer REGEXP '[a-z]'")
        res_lc = db.execute(query_lc)
        rows_lc = res_lc.fetchall()
        print(f"Found {len(rows_lc)} lowercase MECH answers.")
        for row in rows_lc:
            print(f"ID {row[0]}: '{row[1]}'")

            
    finally:
        db.close()


if __name__ == "__main__":
    inspect_eee()
