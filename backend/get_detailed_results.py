from database import SessionLocal
from sqlalchemy import text
import json

def get_detailed_results():
    db = SessionLocal()
    try:
        # Get top users by result count
        top_users = db.execute(text("""
            SELECT username, COUNT(*) as count 
            FROM results 
            GROUP BY username 
            ORDER BY count DESC 
            LIMIT 5
        """)).fetchall()
        
        print(f"Top Users: {top_users}")
        
        results_data = []
        for user_row in top_users:
            user = user_row[0]
            res = db.execute(text("""
                SELECT category, area, score, timestamp 
                FROM results 
                WHERE username = :user
            """), {"user": user}).fetchall()
            
            user_results = []
            for r in res:
                user_results.append({
                    "category": r[0],
                    "area": r[1],
                    "score": r[2],
                    "timestamp": str(r[3])
                })
            results_data.append({
                "username": user,
                "results": user_results
            })
            
        with open("backend/user_results_detailed.json", "w") as f:
            json.dump(results_data, f, indent=4)
            
    finally:
        db.close()

if __name__ == '__main__':
    get_detailed_results()
