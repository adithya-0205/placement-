from database import SessionLocal
from sqlalchemy import text

def remove_option_e():
    db = SessionLocal()
    try:
        # 1. Re-map correct_answer 'E' to 'D'
        print("🔄 Re-mapping correct_answer 'E' to 'D'...")
        res = db.execute(text("UPDATE questions SET correct_answer = 'D' WHERE correct_answer = 'E' OR correct_answer = 'e'"))
        print(f"✅ Updated {res.rowcount} questions.")

        # 2. Check if option_e column exists before dropping
        res = db.execute(text("DESCRIBE questions"))
        columns = [row[0] for row in res]
        
        if 'option_e' in columns:
            print("🧨 Dropping 'option_e' column...")
            db.execute(text("ALTER TABLE questions DROP COLUMN option_e"))
            print("✅ Column dropped successfully.")
        else:
            print("ℹ️ 'option_e' column not found, skipping drop.")
        
        db.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    remove_option_e()
