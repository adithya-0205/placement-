from database import SessionLocal
from sqlalchemy import text

def analyze_performance():
    db = SessionLocal()
    try:
        # Get users and their average scores
        res = db.execute(text("""
            SELECT username, category, AVG(score) as avg_score, COUNT(*) as attempts
            FROM results
            GROUP BY username, category
        """))
        print("Performance Summary:")
        for r in res:
            print(f"User: {r[0]}, Category: {r[1]}, Avg Score: {r[2]}, Attempts: {r[3]}")
        
        # Get weak areas for the most active user
        # Let's assume the user is the one with most results or 'Adithya'
        res = db.execute(text("""
            SELECT username, area, AVG(score) as avg_score, category
            FROM results
            WHERE score < 7
            GROUP BY username, area, category
            ORDER BY avg_score ASC
        """))
        print("\nWeak Areas (Score < 7/10):")
        for r in res:
            print(f"User: {r[0]}, Category: {r[3]}, Area: {r[1]}, Avg Score: {r[2]}")
            
    finally:
        db.close()

if __name__ == '__main__':
    analyze_performance()
