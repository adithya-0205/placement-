import sys
import os

# Add the backend path to sys.path so we can import ai_engine
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from sqlalchemy import text
from ai_engine import call_groq

def fix_with_ai():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT id, question, option_a, option_b, option_c, option_d, option_e FROM questions WHERE branch='MECH' AND LENGTH(TRIM(correct_answer)) != 1"))
        rows = res.fetchall()
        
        for r in rows:
            qid, q_text, opt_a, opt_b, opt_c, opt_d, opt_e = r
            options = f"A: {opt_a}, B: {opt_b}, C: {opt_c}, D: {opt_d}"
            if opt_e: options += f", E: {opt_e}"
            
            prompt = f"For the following technical question, tell me ONLY the letter of the correct answer (A, B, C, D, or E).\n\nQuestion: {q_text}\nOptions: {options}\n\nLetter:"
            
            print(f"Resolving Q{qid} with AI...")
            ai_ans = call_groq(prompt)
            if ai_ans:
                # Extract first A-E found
                import re
                match = re.search(r'([A-E])', ai_ans.upper())
                if match:
                    new_letter = match.group(1)
                    db.execute(text("UPDATE questions SET correct_answer = :ans WHERE id = :id"), {"ans": new_letter, "id": qid})
                    print(f"  ✅ Fixed Q{qid} -> {new_letter}")
                else:
                    print(f"  ⚠️ AI gave weird response: {ai_ans}")
        
        db.commit()
    finally:
        db.close()

if __name__ == '__main__':
    fix_with_ai()
