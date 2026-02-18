from database import SessionLocal
from sqlalchemy import text

def check_mech_options():
    db = SessionLocal()
    try:
        # Check MECH questions for option_e and correct_answer
        res = db.execute(text("SELECT id, option_a, option_b, option_c, option_d, option_e, correct_answer FROM questions WHERE branch='MECH' LIMIT 10"))
        print(f"{'ID':<10} | {'Opt E':<20} | {'Ans':<5}")
        print("-" * 40)
        for row in res:
            opt_e = str(row[5]) if row[5] else "None"
            print(f"{row[0]:<10} | {opt_e[:20]:<20} | {row[6]:<5}")
        
        # Check if any MECH question has 'E' as answer
        e_ans = db.execute(text("SELECT COUNT(*) FROM questions WHERE branch='MECH' AND correct_answer='E'"))
        print(f"\nMECH questions with 'E' as answer: {e_ans.fetchone()[0]}")
        
    finally:
        db.close()

if __name__ == '__main__':
    check_mech_options()
