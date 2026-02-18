import os
import csv
import sys
import time
from sqlalchemy import text
from database import mysql_engine as engine
from ai_engine import enhance_question, parse_ai_response

def import_eee_data():
    """
    Import EEE questions from eee_mcq.csv with AI enhancement.
    Handles 5 options and uses Groq/Llama.
    """
    file_path = "backend/datasets/eee_mcq.csv"
    branch = "EEE"
    category = "technical"
    
    print(f"🚀 Starting AI-enhanced import for {branch} from {file_path}...")
    if not os.path.exists(file_path):
        print(f"❌ Error: {file_path} not found.")
        return

    questions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        questions = [row for row in reader]

    total = len(questions)
    print(f"📋 Total questions to process: {total}")
    print("🤖 Using Groq (Llama-3.3-70b-versatile) for enhancement...")

    with engine.connect() as conn:
        # Get existing questions to skip them
        res = conn.execute(text("SELECT question FROM questions WHERE branch='EEE'"))
        existing_questions = {row[0] for row in res}
        print(f"✅ Found {len(existing_questions)} questions already in DB. Skipping duplicates...")

        for idx, q in enumerate(questions, 1):
            q_text = (q.get('Question') or '').strip()
            if not q_text: continue
            
            # Skip if already imported
            if q_text in existing_questions:
                continue

            opt_a = (q.get('Option_A') or '').strip()
            opt_b = (q.get('Option_B') or '').strip()
            opt_c = (q.get('Option_C') or '').strip()
            opt_d = (q.get('Option_D') or '').strip()
            opt_e = (q.get('Option_E') or '').strip()
            answer_letter = (q.get('Answer') or '').strip().upper()

            # Handle column shift (if Answer is None but Option_E has the answer)
            if not answer_letter and opt_e in ['A', 'B', 'C', 'D', 'E']:
                answer_letter = opt_e
                opt_e = "None"
                print(f"  ⚠️ Fixed column shift for Q{idx}")

            # Format options for AI
            options_text = f"A: {opt_a}, B: {opt_b}, C: {opt_c}, D: {opt_d}, E: {opt_e}"
            
            print(f"  [{idx}/{total}] Processing: {q_text[:60]}...")
            
            # AI Enhancement
            raw_ai = enhance_question(None, q_text, options_text, answer_letter)
            parsed = parse_ai_response(raw_ai)
            
            if parsed and parsed.get("explanation"):
                diff_text = parsed["difficulty_text"]
                diff_level = parsed["difficulty_level"]
                area = parsed["area"]
                exp = parsed["explanation"]
                print(f"    ✅ Success: {area} | Level {diff_level} | {len(exp)} chars")
            else:
                print(f"    ⚠️ AI failed, using default values.")
                diff_text, diff_level, area, exp = 'medium', 5, 'Electrical Engineering', f"The correct answer is {answer_letter}."

            # Insert into database - correctly handling option_e
            conn.execute(text("""
                INSERT INTO questions (question, option_a, option_b, option_c, option_d, option_e, correct_answer, explanation, difficulty, difficulty_level, category, branch, area)
                VALUES (:question, :option_a, :option_b, :option_c, :option_d, :option_e, :correct_answer, :explanation, :difficulty, :difficulty_level, :category, :branch, :area)
            """), {
                'question': q_text, 
                'option_a': opt_a, 
                'option_b': opt_b, 
                'option_c': opt_c, 
                'option_d': opt_d, 
                'option_e': opt_e,
                'correct_answer': answer_letter, 
                'explanation': exp, 
                'difficulty': diff_text, 
                'difficulty_level': diff_level,
                'category': category, 
                'branch': branch, 
                'area': area
            })
            
            # Commit every question for safety (since AI is slow and we don't want to lose progress)
            conn.commit()
            
            # Rate limiting for Groq
            time.sleep(1.2)

    print(f"\n✨ Successfully imported and enhanced {total} EEE questions!")

if __name__ == "__main__":
    try:
        import_eee_data()
    except KeyboardInterrupt:
        print("\n\n🛑 Import interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
