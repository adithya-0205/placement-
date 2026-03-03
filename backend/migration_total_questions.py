import pymysql

def migrate():
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='',
            database='placement_app'
        )
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("SHOW COLUMNS FROM results LIKE 'total_questions'")
        if not cursor.fetchone():
            print("Adding total_questions column to results table...")
            cursor.execute("ALTER TABLE results ADD COLUMN total_questions INT DEFAULT 10 AFTER score")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column total_questions already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == '__main__':
    migrate()
