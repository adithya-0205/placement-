from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """User model for authentication and progress tracking"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    aptitude_level = Column(Integer, default=1)
    technical_level = Column(Integer, default=1)
    branch = Column(String(50))
    role = Column(String(20), default='student')
    last_level_update = Column(TIMESTAMP, server_default=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())


class Score(Base):
    """Score/Results model for tracking quiz performance"""
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, default=10)
    area = Column(String(100))
    timestamp = Column(TIMESTAMP, server_default=func.now())


class Question(Base):
    """Question model for storing quiz questions"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    correct_answer = Column(Text)
    category = Column(String(50))
    area = Column(String(100))
    difficulty = Column(String(20))
    explanation = Column(Text)
    branch = Column(String(50))
    difficulty_level = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())


class GDEvaluation(Base):
    """Model for storing Group Discussion evaluations"""
    __tablename__ = "gd_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255))
    topic = Column(Text)
    transcript = Column(Text)
    content_score = Column(Integer)
    communication_score = Column(Integer)
    feedback = Column(Text)
    audio_path = Column(String(500))
    timestamp = Column(TIMESTAMP, server_default=func.now())


class WeeklyStat(Base):
    """Model for tracking historical weekly performance"""
    __tablename__ = "weekly_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    week_start_date = Column(TIMESTAMP, server_default=func.now())
    avg_score = Column(Integer)  # Aggregate score across all modules
    is_level_up = Column(Integer, default=0)
    total_activities = Column(Integer, default=0)