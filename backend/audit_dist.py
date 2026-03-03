import pymysql

def audit_areas():
    conn = pymysql.connect(host='127.0.0.1', user='root', password='', database='placement_app')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT category, branch, area, COUNT(*) as cnt FROM questions GROUP BY category, branch, area")
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"{row['category']} | {row['branch']} | {row['area']}: {row['cnt']}")
    
    conn.close()

if __name__ == "__main__":
    audit_areas()
