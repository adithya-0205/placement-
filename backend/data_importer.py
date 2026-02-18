import os
import csv
import sys
import time
from sqlalchemy import text
from database import mysql_engine as engine
from ai_engine import enhance_question, parse_ai_response

def import_branch_data(file_path, branch, category="technical", use_ai=False):
    """
    Complete logic for importing branch-specific questions.
    Supports AI enhancement during import like import_mech_questions.py.
    """
    print(f"Importing {branch} {category} from {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    questions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        questions = [row for row in reader]

    print(f"Total questions to process: {len(questions)}")
    
    with engine.connect() as conn:
        for idx, q in enumerate(questions, 1):
            q_text = q.get('question', '').strip()
            # Support both optiona/option_a headers
            opt_a = q.get('optiona') or q.get('option_a', '')
            opt_b = q.get('optionb') or q.get('option_b', '')
            opt_c = q.get('optionc') or q.get('option_c', '')
            opt_d = q.get('optiond') or q.get('option_d', '')
            answer = (q.get('answer') or q.get('correct_answer', '')).strip().upper()

            # Default values
            diff_text, diff_level, area, exp = 'medium', 5, branch, f"The correct answer is {answer}."

            if use_ai:
                print(f"  [{idx}/{len(questions)}] AI Enhancement for: {q_text[:50]}...")
                raw_ai = enhance_question(None, q_text, f"A: {opt_a}, B: {opt_b}, C: {opt_c}, D: {opt_d}", answer)
                parsed = parse_ai_response(raw_ai)
                if parsed and parsed["explanation"]:
                    diff_text, diff_level, area, exp = parsed["difficulty_text"], parsed["difficulty_level"], parsed["area"], parsed["explanation"]
                time.sleep(1) # Simple rate limit

            conn.execute(text("""
                INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, explanation, difficulty, difficulty_level, category, branch, area)
                VALUES (:question, :option_a, :option_b, :option_c, :option_d, :correct_answer, :explanation, :difficulty, :difficulty_level, :category, :branch, :area)
            """), {
                'question': q_text, 'option_a': opt_a, 'option_b': opt_b, 'option_c': opt_c, 'option_d': opt_d,
                'correct_answer': answer, 'explanation': exp, 'difficulty': diff_text, 'difficulty_level': diff_level,
                'category': category, 'branch': branch.upper(), 'area': area
            })
            
            if idx % 10 == 0:
                conn.commit()
                print(f"  Committed {idx} questions.")
        conn.commit()
    print(f"✅ Import complete for {branch}.")

if __name__ == "__main__":
    if len(sys.argv) > 3:
        file = sys.argv[1]
        branch = sys.argv[2]
        ai_flag = sys.argv[3].lower() == "true"
        import_branch_data(file, branch, use_ai=ai_flag)
    else:
        print("Usage: python data_importer.py <csv_path> <branch> <use_ai_true/false>")
