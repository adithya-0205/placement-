from database import SessionLocal
from sqlalchemy import text

def analyze_performance():
    db = SessionLocal()
    try:
        # Get all results
        res = db.execute(text("""
            SELECT username, category, area, score, timestamp
            FROM results
            ORDER BY username, category, timestamp DESC
        """))
        
        print("FULL RESULTS DUMP:")
        print("-" * 50)
        for r in res:
            print(f"User: {r[0]} | Cat: {r[1]} | Area: {r[2]} | Score: {r[3]} | Time: {r[4]}")
        print("-" * 50)
        
    finally:
        db.close()

if __name__ == '__main__':
    analyze_performance()
