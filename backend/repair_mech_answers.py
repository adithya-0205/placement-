import re
from database import SessionLocal
from sqlalchemy import text

def repair_mech_answers():
    db = SessionLocal()
    try:
        # Get all MECH questions where correct_answer is not a single letter
        query = text("""
            SELECT id, question, option_a, option_b, option_c, option_d, option_e, correct_answer, explanation 
            FROM questions 
            WHERE branch='MECH' AND LENGTH(TRIM(correct_answer)) != 1
        """)
        rows = db.execute(query).fetchall()
        
        print(f"🚀 Found {len(rows)} MECH questions to repair.")
        repaired_count = 0
        
        for r in rows:
            qid, q_text, opt_a, opt_b, opt_c, opt_d, opt_e, cur_ans, exp = r
            cur_ans = str(cur_ans).strip()
            new_ans = None
            
            # 1. Pattern Matching (e.g. B'FOR -> B)
            match = re.match(r'^([A-E])[\'":\s]', cur_ans.upper())
            if match:
                new_ans = match.group(1)
                
            # 2. Text Matching with Options
            if not new_ans:
                ans_text = cur_ans.lower()
                for letter, opt in zip(['A', 'B', 'C', 'D', 'E'], [opt_a, opt_b, opt_c, opt_d, opt_e]):
                    if opt and ans_text in str(opt).lower():
                        new_ans = letter
                        break
            
            # 3. Explanation Parsing
            if not new_ans and exp:
                match_exp = re.search(r'(?i)correct answer is ([A-E])', exp)
                if match_exp:
                    new_ans = match_exp.group(1)
            
            # 4. Handle "ANSWE" (Assume it might be in explanation if not found by regex)
            if not new_ans and "ANSWE" in cur_ans.upper() and exp:
                 # Look for any single A, B, C, D, E at the end of explanation or near "Answer"
                 match_ans = re.search(r'(?i)Answer[:\s]+([A-E])', exp)
                 if match_ans:
                     new_ans = match_ans.group(1)

            if new_ans:
                db.execute(
                    text("UPDATE questions SET correct_answer = :ans WHERE id = :id"),
                    {"ans": new_ans, "id": qid}
                )
                repaired_count += 1
                # print(f"  ✅ Fixed Q{qid}: '{cur_ans}' -> {new_ans}")
            else:
                print(f"  ❌ Failed to fix Q{qid}: '{cur_ans}'")
        
        db.commit()
        print(f"\n✨ Repaired {repaired_count}/{len(rows)} questions.")
        
    except Exception as e:
        print(f"Error during repair: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    repair_mech_answers()
