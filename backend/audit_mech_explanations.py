from database import SessionLocal
from sqlalchemy import text

def audit_mech_explanations():
    db = SessionLocal()
    try:
        # Get examples of malformed questions and their explanations
        query = text("""
            SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, explanation 
            FROM questions 
            WHERE branch='MECH' AND LENGTH(TRIM(correct_answer)) != 1
            LIMIT 20
        """)
        res = db.execute(query)
        rows = res.fetchall()
        
        print(f"--- Detailed Audit of {len(rows)} Malformed MECH Questions ---")
        for r in rows:
            print(f"ID: {r[0]}")
            print(f"CURRENT ANS: '{r[6]}'")
            exp = r[7] if r[7] else "None"
            print(f"EXPLANATION: {exp[:150]}...")
            
            # Simple letter extraction from explanation trial
            import re
            match = re.search(r'(?i)correct answer is ([A-E])', exp)
            if match:
                print(f"✅ FOUND IN EXP: {match.group(1)}")
            else:
                print("❌ NOT FOUND IN EXP")
            print("-" * 30)
                
    finally:
        db.close()

if __name__ == '__main__':
    audit_mech_explanations()
