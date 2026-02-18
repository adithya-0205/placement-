from database import SessionLocal
from main import get_todays_questions
from sqlalchemy import text
import unittest
from datetime import date

class TestQuizFetch(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Ensure we have a test user with EEE branch
        self.username = "test_eee_user"
        self.db.execute(text("DELETE FROM users WHERE username = :u"), {"u": self.username})
        self.db.execute(text("""
            INSERT INTO users (username, password_hash, branch, aptitude_level, technical_level)
            VALUES (:u, 'pass', 'EEE', 1, 3)
        """), {"u": self.username})
        
        # Clear daily quiz for today to force regeneration
        self.db.execute(text("DELETE FROM daily_quiz WHERE username = :u"), {"u": self.username})
        self.db.commit()

    def tearDown(self):
        self.db.execute(text("DELETE FROM users WHERE username = :u"), {"u": self.username})
        self.db.execute(text("DELETE FROM daily_quiz WHERE username = :u"), {"u": self.username})
        self.db.commit()
        self.db.close()

    def test_eee_hard_tech_quiz(self):
        print("\nTesting EEE Technical Quiz (Level 3 - Hard)...")
        # EEE Hard only has 3 questions in DB. Should fallback to pull more.
        question_ids = get_todays_questions(self.db, self.username, "technical")
        
        print(f"Fetched {len(question_ids)} questions: {question_ids}")
        self.assertEqual(len(question_ids), 10, f"Expected 10 questions, but got {len(question_ids)}")
        
        # Verify they are all EEE questions
        placeholders = ",".join(map(str, question_ids))
        res = self.db.execute(text(f"SELECT COUNT(*) FROM questions WHERE id IN ({placeholders}) AND LOWER(branch) LIKE '%eee%'"))
        count = res.fetchone()[0]
        self.assertEqual(count, 10, "Not all fetched questions are from EEE branch")
        print("✅ EEE Hard fallback test passed!")

    def test_eee_easy_tech_quiz(self):
        print("\nTesting EEE Technical Quiz (Level 1 - Easy)...")
        # EEE Easy has 39 questions. Should get 10 easily.
        self.db.execute(text("UPDATE users SET technical_level = 1 WHERE username = :u"), {"u": self.username})
        self.db.execute(text("DELETE FROM daily_quiz WHERE username = :u"), {"u": self.username})
        self.db.commit()
        
        question_ids = get_todays_questions(self.db, self.username, "technical")
        print(f"Fetched {len(question_ids)} questions: {question_ids}")
        self.assertEqual(len(question_ids), 10)
        print("✅ EEE Easy test passed!")

if __name__ == '__main__':
    unittest.main()
