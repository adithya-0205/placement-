import pymysql

def verify():
    conn = pymysql.connect(host='127.0.0.1', user='root', password='', database='placement_app')
    cursor = conn.cursor()
    
    # Get latest quiz for Adithya
    print("Checking Adithya's latest technical quiz...")
    cursor.execute("SELECT question_ids FROM daily_quiz WHERE username = 'Adithya' AND category = 'technical' ORDER BY quiz_date DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("No quiz found for Adithya.")
        return
        
    ids = row[0]
    print(f"Question IDs: {ids}")
    
    # Get area distribution
    cursor.execute(f"SELECT area, COUNT(*) FROM questions WHERE id IN ({ids}) GROUP BY area")
    results = cursor.fetchall()
    
    print("\nTopic Distribution for today's quiz:")
    for area, count in results:
        print(f"- {area}: {count}")
    
    conn.close()

if __name__ == "__main__":
    verify()
