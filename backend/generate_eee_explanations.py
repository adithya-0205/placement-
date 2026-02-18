from database import SessionLocal
from sqlalchemy import text
from ai_engine import enhance_question, parse_ai_response
import time

def process_eee_batch():
    db = SessionLocal()
    try:
        # Groq Health Check
        print("🔍 Checking Groq connectivity...")
        test_res = enhance_question(0, "Test Question", "A: Yes, B: No", "A")
        if not test_res:
            print("❌ Groq integration failed. Check GROQ_API_KEY.")
            return
        else:
            print("✅ Groq integration working!")

        # Get EEE questions missing explanations or having placeholders
        # Using more flexible query to catch variations
        query = text("""
            SELECT id, question, option_a, option_b, option_c, option_d, correct_answer 
            FROM questions 
            WHERE (LOWER(branch) = 'eee' OR branch LIKE '%EEE%')
            AND (explanation IS NULL 
                 OR explanation = '' 
                 OR explanation = 'No explanation provided.' 
                 OR explanation = 'Explanation generation failed.'
                 OR explanation LIKE 'The correct answer is %')
        """)
        rows = db.execute(query).fetchall()

        
        total = len(rows)
        print(f"🚀 Starting Groq batch process for {total} EEE questions...")
        
        for idx, row in enumerate(rows, 1):
            qid = row[0]
            print(f"[{idx}/{total}] Processing QID: {qid}...")
            
            options_text = f"A: {row[2]}, B: {row[3]}, C: {row[4]}, D: {row[5]}"
            
            try:
                raw_ai = enhance_question(qid, row[1], options_text, row[6])
                parsed = parse_ai_response(raw_ai)
                
                if parsed and parsed.get("explanation"):
                    db.execute(text("""
                        UPDATE questions 
                        SET explanation = :exp, area = :area, difficulty_level = :dl, difficulty = :dt 
                        WHERE id = :id
                    """), {
                        "exp": parsed["explanation"],
                        "area": parsed["area"],
                        "dl": parsed["difficulty_level"],
                        "dt": parsed["difficulty_text"],
                        "id": qid
                    })
                    db.commit()
                    print(f"  ✅ Saved explanation for Q{qid}")
                else:
                    print(f"  ⚠️ AI failed for Q{qid}")
            except Exception as e:
                print(f"  ❌ Error for Q{qid}: {e}")
            
            # Groq Rate Limiting
            time.sleep(1.0)

    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    process_eee_batch()
