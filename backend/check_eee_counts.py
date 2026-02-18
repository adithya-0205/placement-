from database import SessionLocal
from sqlalchemy import text

def check_counts():
    db = SessionLocal()
    try:
        with open('backend/branch_check_results.txt', 'w') as f:
            # Check counts by branch and category
            result = db.execute(text("SELECT branch, category, difficulty, COUNT(*) FROM questions GROUP BY branch, category, difficulty"))
            f.write(f"{'Branch':<20} | {'Category':<15} | {'Difficulty':<10} | {'Count':<5}\n")
            f.write("-" * 60 + "\n")
            for row in result:
                f.write(f"{str(row[0]):<20} | {str(row[1]):<15} | {str(row[2]):<10} | {row[3]}\n")
            
            # Check specifically for EEE
            f.write("\nChecking EEE specifically:\n")
            eee_branches = db.execute(text("SELECT DISTINCT branch FROM questions WHERE LOWER(branch) LIKE '%eee%'")).fetchall()
            f.write(f"Distinct EEE branch strings in DB: {[r[0] for r in eee_branches]}\n")
            
            eee_result = db.execute(text("SELECT COUNT(*) FROM questions WHERE LOWER(branch) LIKE '%eee%'"))
            f.write(f"Total EEE questions (any category): {eee_result.fetchone()[0]}\n")

            
            # Check EEE Technical Easy
            eee_easy = db.execute(text("SELECT COUNT(*) FROM questions WHERE LOWER(branch) LIKE '%eee%' AND category='technical' AND difficulty='Easy'"))
            f.write(f"EEE Technical Easy: {eee_easy.fetchone()[0]}\n")

    finally:
        db.close()

if __name__ == '__main__':
    check_counts()
