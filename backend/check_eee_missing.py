from database import SessionLocal
from sqlalchemy import text

def check_eee_missing():
    db = SessionLocal()
    try:
        # Check specifically for EEE
        query = text("""
            SELECT COUNT(*) FROM questions 
            WHERE branch='EEE' 
            AND (explanation IS NULL 
                 OR explanation = '' 
                 OR explanation = 'No explanation provided.' 
                 OR explanation = 'Explanation generation failed.')
        """)
        res = db.execute(query)
        count = res.fetchone()[0]
        print(f"EEE questions missing meaningful explanations: {count}")
        
        # Check total EEE questions
        res_total = db.execute(text("SELECT COUNT(*) FROM questions WHERE branch='EEE'"))
        total = res_total.fetchone()[0]
        print(f"Total EEE questions: {total}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_eee_missing()
