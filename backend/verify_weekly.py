import pymysql
from datetime import date, timedelta, datetime, time

def verify_distribution():
    conn = pymysql.connect(host='127.0.0.1', user='root', password='', database='placement_app')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 1. Identify Week Start (Monday)
    today_dt = date.today()
    week_start = today_dt - timedelta(days=today_dt.weekday())
    week_start_ts = datetime.combine(week_start, time.min)
    
    print(f"Checking distribution for week starting: {week_start_ts}")
    
    # 2. Get distribution from results
    distribution_query = """
        SELECT area, SUM(total_questions) as count 
        FROM results 
        WHERE username = 'Adithya' 
        AND category = 'TECHNICAL' 
        AND timestamp >= %s
        GROUP BY area
    """
    cursor.execute(distribution_query, (week_start_ts,))
    rows = cursor.fetchall()
    
    if not rows:
        print("No quiz results found for Adithya this week.")
        return
        
    print("\nWeekly Topic Distribution so far:")
    for row in rows:
        print(f"- {row['area']}: {row['count']} questions")
        
    # 3. Simulate deficit logic (conceptually)
    # Get all distinct areas in DB
    cursor.execute("SELECT DISTINCT area FROM questions WHERE category = 'technical' AND branch LIKE '%CSE%'")
    all_areas = [r['area'] for r in cursor.fetchall()]
    num_areas = len(all_areas)
    target = 70.0 / num_areas
    
    print(f"\nTarget per area for the week: {target:.2f}")
    
    conn.close()

if __name__ == "__main__":
    verify_distribution()
