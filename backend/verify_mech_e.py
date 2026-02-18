from database import SessionLocal
from main import get_questions_by_ids
from sqlalchemy import text

def verify_mech_e():
    db = SessionLocal()
    try:
        # Get a MECH question with option_e
        res = db.execute(text("SELECT id FROM questions WHERE branch='MECH' AND option_e IS NOT NULL AND option_e != '' LIMIT 1"))
        row = res.fetchone()
        if not row:
            print("No MECH questions with option_e found for testing.")
            return
        
        qid = row[0]
        questions = get_questions_by_ids(db, [qid])
        
        if questions:
            q = questions[0]
            print(f"ID: {q['id']}")
            print(f"Options: {q['options']}")
            print(f"Answer: {q['answer']}")
            
            if len(q['options']) == 5:
                print("✅ Success: Fetched 5 options!")
            else:
                print(f"❌ Failure: Fetched {len(q['options'])} options.")
        else:
            print("❌ Failure: No question details returned.")
            
    finally:
        db.close()

if __name__ == '__main__':
    verify_mech_e()
