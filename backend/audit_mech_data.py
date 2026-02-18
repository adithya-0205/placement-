from database import SessionLocal
from sqlalchemy import text

def audit_mech_data():
    db = SessionLocal()
    try:
        # Get examples of malformed questions
        query = text("""
            SELECT id, question, option_a, option_b, option_c, option_d, option_e, correct_answer 
            FROM questions 
            WHERE branch='MECH' AND LENGTH(TRIM(correct_answer)) != 1
            LIMIT 50
        """)

        res = db.execute(query)
        rows = res.fetchall()
        
        print(f"--- Detailed Audit of {len(rows)} Malformed MECH Questions ---")
        for r in rows:
            print(f"ID: {r[0]}")
            print(f"Question: {r[1][:50]}...")
            print(f"A: {r[2]}")
            print(f"B: {r[3]}")
            print(f"C: {r[4]}")
            print(f"D: {r[5]}")
            if r[6]: print(f"E: {r[6]}")
            print(f"CURRENT ANS: '{r[7]}'")
            
            # See if we can find a match
            ans_text = str(r[7]).lower().strip()
            found = False
            for letter, opt in zip(['A', 'B', 'C', 'D', 'E'], [r[2], r[3], r[4], r[5], r[6]]):
                if opt and ans_text in str(opt).lower():
                    print(f"🔍 POTENTIAL MATCH: {letter} ('{opt}')")
                    found = True
            if not found:
                print("❌ NO EASY MATCH FOUND")
            print("-" * 30)
            
        # Describe table schema
        print("\n--- Schema Check ---")
        res = db.execute(text("DESCRIBE questions"))
        for row in res:
            if row[0] == 'correct_answer':
                print(f"Column '{row[0]}' is of type: {row[1]}")
                
    finally:
        db.close()

if __name__ == '__main__':
    audit_mech_data()
