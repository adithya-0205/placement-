# Ways to View MySQL Database

## Option 1: Using Python Script (Quickest)
```bash
cd backend
python view_database.py
```

## Option 2: MySQL Command Line
```bash
# Connect to MySQL
mysql -u root -p

# Once connected:
USE placement_app;
SHOW TABLES;
SELECT COUNT(*) FROM questions WHERE branch='ECE';
SELECT * FROM questions WHERE branch='ECE' LIMIT 5;
```

## Option 3: MySQL Workbench (GUI - Best for browsing)
1. Download MySQL Workbench: https://dev.mysql.com/downloads/workbench/
2. Install and open
3. Create connection:
   - Hostname: 127.0.0.1
   - Port: 3306
   - Username: root
   - Password: (your MySQL password)
4. Connect and browse tables visually

## Option 4: phpMyAdmin (Web-based GUI)
1. Install XAMPP or WAMP (includes phpMyAdmin)
2. Access: http://localhost/phpmyadmin
3. Login with MySQL credentials
4. Browse placement_app database

## Option 5: DBeaver (Free Universal Database Tool)
1. Download: https://dbeaver.io/download/
2. Install and create MySQL connection
3. Browse database visually

## Option 6: VS Code Extension
1. Install "MySQL" extension in VS Code
2. Add connection with your MySQL credentials
3. Browse database in VS Code sidebar

## Quick Check Commands
```bash
# Count all questions
python -c "from database import get_db; from sqlalchemy import text; db = next(get_db()); r = db.execute(text('SELECT COUNT(*) FROM questions')); print(f'Total: {r.scalar()}')"

# Count ECE questions
python -c "from database import get_db; from sqlalchemy import text; db = next(get_db()); r = db.execute(text('SELECT COUNT(*) FROM questions WHERE branch=\"ECE\"')); print(f'ECE: {r.scalar()}')"
```

## Database Connection Details
- **Host**: 127.0.0.1 (localhost)
- **Port**: 3306
- **Database**: placement_app
- **Username**: root
- **Password**: (check your .env file or MySQL setup)
