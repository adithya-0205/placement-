from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
import whisper 
import ollama  
import json    
import os
import random
import traceback
import sys
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime, timedelta, time
import pymysql
from concurrent.futures import ThreadPoolExecutor
import re
from typing import List, Dict, Optional
from question_generator import generate_questions_ai

from database import get_db, init_db, test_connection, SessionLocal, mysql_engine as engine

# --- MODELS ---
class UserAuth(BaseModel):
    username: str
    password: str
    branch: Optional[str] = None
    role: Optional[str] = 'student'

class QuizRequest(BaseModel):
    username: str
    category: str
    target_branch: Optional[str] = None # Added for practice mode

class AnswerSubmission(BaseModel):
    username: str
    category: str
    question_id: int
    user_answer: str

class QuizCompleteSubmission(BaseModel):
    username: str
    category: str
    score: int
    total_questions: int
    target_branch: Optional[str] = None # Added for practice mode
    weak_area: Optional[str] = None # Added for analytics

class QuizResult(BaseModel):
    username: str
    category: str
    score: int
    area: str

class UpdateBranchRequest(BaseModel):
    username: str
    branch: str

# Load Whisper model once at startup
stt_model = whisper.load_model("base")

def process_weekly_level_up(username: str, db: Session):
    """
    Fluid Level-Up Logic
    - Rule: Must complete 7 days of daily quizzes + 1 GD + 1 Interview to unlock next level.
    - Trigger: Anytime the requirement is met since the last Level Update.
    """
    try:
        today = date.today()
        
        # Get user
        user_result = db.execute(
            text("SELECT aptitude_level, technical_level, last_level_update FROM users WHERE username = :u"),
            {"u": username}
        )
        user = user_result.fetchone()
        if not user: return False
        
        apt_lvl, tech_lvl, last_update = user
        # Default last_update to 7 days ago if null to allow first-time check
        if not last_update:
            last_update = datetime.now() - timedelta(days=7)
            
        # 1. Aggregate Activity percentage since LAST UPDATE
        activity_counts = db.execute(
            text("""
                SELECT category, COUNT(*) as count, SUM(score) as total_s, SUM(total_questions) as total_q
                FROM results 
                WHERE username = :u 
                AND timestamp >= :last_up
                GROUP BY category
            """),
            {"u": username, "last_up": last_update}
        ).fetchall()
        
        # Calculate percentage: (total_score / total_questions) * 100
        stats = {}
        for row in activity_counts:
            cat = row[0].upper()
            cnt = row[1]
            t_s = row[2] or 0
            t_q = row[3] or 1 # prevent zero division
            
            # If total_questions is missing or 0 in DB, default to out of 10 for quizzes, 100 for GD/Interview
            if t_q == 0 or t_q == 1:
                 t_q = 100 if cat in ['GD', 'INTERVIEW'] else (cnt * 10)
                 
            percent = (t_s / t_q) * 100
            stats[cat] = {"count": cnt, "avg_percent": percent}

        # Count distinct days where both Aptitude and Technical were completed since last update
        dual_completion_res = db.execute(
            text("""
                SELECT COUNT(*) FROM (
                    SELECT DATE(timestamp) as d
                    FROM results 
                    WHERE username = :u 
                    AND category IN ('APTITUDE', 'TECHNICAL')
                    AND timestamp >= :last_up
                    GROUP BY DATE(timestamp)
                    HAVING COUNT(DISTINCT category) = 2
                ) as t
            """),
            {"u": username, "last_up": last_update}
        ).fetchone()
        
        days_completed = dual_completion_res[0] or 0

        # 2. Strict Requirements Check (Since last update)
        gd_sessions = stats.get('GD', {}).get('count', 0)
        interview_sessions = stats.get('INTERVIEW', {}).get('count', 0)

        # Percentages for quality check
        apt_percent = stats.get('APTITUDE', {}).get('avg_percent', 0)
        tech_percent = stats.get('TECHNICAL', {}).get('avg_percent', 0)
        gd_percent = stats.get('GD', {}).get('avg_percent', 0)
        interview_percent = stats.get('INTERVIEW', {}).get('avg_percent', 0)

        # Require 7 distinct days + 75% across required categories
        can_level_up_apt = (days_completed >= 7 and apt_percent >= 75)
        can_level_up_tech = (days_completed >= 7 and tech_percent >= 75 and gd_percent >= 75 and interview_percent >= 75)

        # 3. Level Up Logic
        new_apt_lvl = apt_lvl
        if can_level_up_apt and apt_lvl < 4:
            new_apt_lvl += 1
            
        new_tech_lvl = tech_lvl
        if can_level_up_tech and tech_lvl < 4:
            new_tech_lvl += 1
            new_tech_lvl += 1

        level_up_occurred = (new_apt_lvl > apt_lvl or new_tech_lvl > tech_lvl)

        # 4. Save to weekly_stats
        overall_avg = (apt_percent + tech_percent) / 2 if (apt_percent > 0 and tech_percent > 0) else (apt_percent or tech_percent)
        
        db.execute(
            text("""
                INSERT INTO weekly_stats (username, week_start_date, avg_score, is_level_up, total_activities)
                VALUES (:u, :d, :s, :lu, :cnt)
            """),
            {
                "u": username,
                "d": today - timedelta(days=6), # Record the starting Monday
                "s": overall_avg,
                "lu": 1 if level_up_occurred else 0,
                "cnt": days_completed + gd_sessions + interview_sessions
            }
        )

        # 5. Update User Levels
        db.execute(
            text("""
                UPDATE users SET 
                aptitude_level = :al, 
                technical_level = :tl, 
                last_level_update = NOW() 
                WHERE username = :u
            """),
            {"al": new_apt_lvl, "tl": new_tech_lvl, "u": username}
        )
        
        db.commit()
        return level_up_occurred

    except Exception as e:
        print(f"❌ Error in weekly level up: {e}")
        db.rollback()
        return False

def get_user_level(db: Session, username: str, category: str):

    """Get user's current difficulty level"""
    result = db.execute(
        text("SELECT aptitude_level, technical_level FROM users WHERE username = :username"),
        {"username": username}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    level = user[0] if category.lower() == "aptitude" else user[1]
    
    # Map level to difficulty
    if level == 1:
        return "Easy"
    elif level == 2:
        return "Medium"
    elif level == 3:
        return "Hard"
    else:
        return "Company-level"

def get_todays_questions(db: Session, username: str, category: str, target_branch: str = None):
    """Get 10 questions for today - avoiding repeats from previous days"""
    today = date.today()
    
    # If target_branch is provided and DOES NOT MATCH user's branch, do NOT cache/use daily_quiz
    # This is "Practice Mode"
    
    user_result = db.execute(
        text("SELECT branch FROM users WHERE username = :username"),
        {"username": username}
    )
    user_row = user_result.fetchone()
    user_actual_branch = user_row[0] if user_row else None

    is_practice_mode = False
    if category.lower() == "technical" and target_branch and target_branch != user_actual_branch:
        is_practice_mode = True
        print(f"🎯 Practice Mode: User {username} ({user_actual_branch}) practicing {target_branch}")
    
    # Check if user already has questions for today (ONLY if not practice mode)
    if not is_practice_mode:
        result = db.execute(
            text("""
                SELECT question_ids FROM daily_quiz 
                WHERE username = :username 
                AND category = :category 
                AND quiz_date = :today
            """),
            {"username": username, "category": category.lower(), "today": today}
        )
        
        existing = result.fetchone()
        
        if existing and existing[0]:
            # Return existing question IDs, but VERIFY they still exist
            # This prevents returning fewer than 10 questions if some were deleted during updates
            try:
                id_list = [int(x) for x in existing[0].split(",")]
                placeholders = ",".join([str(x) for x in id_list])
                verify_result = db.execute(text(f"SELECT id FROM questions WHERE id IN ({placeholders})")).fetchall()
                verified_ids = [r[0] for r in verify_result]
                
                if len(verified_ids) == len(id_list) and len(verified_ids) >= 1:
                    return verified_ids
                else:
                    print(f"⚠️ Cache mismatch for {username}: {len(verified_ids)}/{len(id_list)} IDs found. Regenerating...")
            except Exception as e:
                print(f"⚠️ Error verifying cached IDs: {e}. Regenerating...")
    
    # Get all past questions to avoid repetition (Skip for practice mode to allow unlimited practice?)
    # Let's keep avoiding repetition for practice mode too to keep it fresh
    past_quizzes = db.execute(
        text("""
            SELECT question_ids FROM daily_quiz 
            WHERE username = :username 
            AND category = :category
        """),
        {"username": username, "category": category.lower()}
    ).fetchall()

    seen_ids = set()
    for row in past_quizzes:
        if row[0]:
            for qid in row[0].split(','):
                try:
                    seen_ids.add(int(qid))
                except ValueError:
                    pass

    # Get user level for difficulty
    difficulty = get_user_level(db, username, category)

    # Fetch ALL candidate questions for this category & difficulty
    if category.lower() == "technical":
        # Use target_branch if provided, otherwise user's actual branch
        branch_to_use = target_branch if target_branch else user_actual_branch
        
        # Map AEI to ECE for technical questions
        if branch_to_use and branch_to_use.upper() == 'AEI':
            branch_to_use = 'ECE'
            
        if branch_to_use:
            # Fetch candidate questions where the requested branch is in the comma-separated branch list
            # We use FIND_IN_SET and REPLACE to handle possible spaces in the DB values
            candidates_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE category = :category 
                    AND LOWER(difficulty) = LOWER(:difficulty)
                    AND (
                        LOWER(branch) = LOWER(:branch)
                        OR FIND_IN_SET(LOWER(:branch), REPLACE(LOWER(branch), ' ', ''))
                    )
                """),
                {"category": category.lower(), "difficulty": difficulty, "branch": branch_to_use.upper()}
            )
        else:
            # No branch set - return empty (user must select branch)
            candidates_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE category = :category 
                    AND LOWER(difficulty) = LOWER(:difficulty)
                    AND 1=0
                """),
                {"category": category.lower(), "difficulty": difficulty}
            )
    else:
        # Aptitude/GD - pull 'Common' branch, empty string, or NULL branch questions
        candidates_result = db.execute(
            text("""
                SELECT id FROM questions 
                WHERE LOWER(category) = LOWER(:category) 
                AND LOWER(difficulty) = LOWER(:difficulty)
                AND (LOWER(branch) = 'common' OR branch IS NULL OR branch = '')
            """),
            {"category": category, "difficulty": difficulty}
        )

    
    all_candidate_ids = [row[0] for row in candidates_result.fetchall()]
    
    # FALLBACK: If fewer than 10 questions found for specific difficulty, try other difficulties for this branch/category
    if len(all_candidate_ids) < 10:
        print(f"🔍 Only {len(all_candidate_ids)} questions for {category} at {difficulty} level. Pulling from other difficulties...")
        
        if category.lower() == "technical" and branch_to_use:
            # Pull ALL questions for this branch regardless of difficulty
            fallback_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE category = :category 
                    AND (
                        LOWER(branch) = LOWER(:branch)
                        OR FIND_IN_SET(LOWER(:branch), REPLACE(LOWER(branch), ' ', ''))
                    )
                """),
                {"category": category.lower(), "branch": branch_to_use.upper()}
            )
            all_candidate_ids = [row[0] for row in fallback_result.fetchall()]
        elif category.lower() != "technical":
            # For Aptitude/GD, pull all 'Common', empty, or NULL questions regardless of difficulty
            fallback_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE LOWER(category) = LOWER(:category) 
                    AND (LOWER(branch) = 'common' OR branch IS NULL OR branch = '')
                """),
                {"category": category}
            )
            all_candidate_ids = [row[0] for row in fallback_result.fetchall()]

            
        print(f"✅ Total available questions for {category}: {len(all_candidate_ids)}")

    
    # --- IMPROVED: WEEKLY TOPIC BALANCING LOGIC ---
    
    # 1. Identify Week Start (Monday)
    today_dt = date.today()
    week_start = today_dt - timedelta(days=today_dt.weekday())
    week_start_ts = datetime.combine(week_start, time.min)
    
    # 2. Get all distinct areas for this branch/category
    branch_val = branch_to_use.upper() if (category.lower() == "technical" and branch_to_use) else "COMMON"
    area_query = """
        SELECT DISTINCT area FROM questions 
        WHERE category = :category 
        AND (LOWER(branch) = LOWER(:branch) OR FIND_IN_SET(LOWER(:branch), REPLACE(LOWER(branch), ' ', '')) OR :branch = 'COMMON')
        AND area IS NOT NULL AND area != ''
    """
    distinct_raw = db.execute(text(area_query), {"category": category.lower(), "branch": branch_val}).fetchall()
    distinct_areas = [r[0] for r in distinct_raw]
    
    if not distinct_areas:
        distinct_areas = ["General"]
    
    # 3. Get current weekly distribution from results table
    distribution_query = """
        SELECT area, SUM(total_questions) as count 
        FROM results 
        WHERE username = :username 
        AND category = :category 
        AND timestamp >= :week_start
        GROUP BY area
    """
    db_counts = db.execute(text(distribution_query), {
        "username": username,
        "category": category.upper(),
        "week_start": week_start_ts
    }).fetchall()
    
    current_counts = {area: 0 for area in distinct_areas}
    for row in db_counts:
        area_name = row[0]
        if area_name in current_counts:
            current_counts[area_name] = int(row[1])
    
    # 4. Selection Algorithm: Deficit-Based (Highest Deficit First)
    # Target: 70 questions per week shared among topics
    target_per_area = 70.0 / len(distinct_areas)
    
    question_ids = []
    temp_counts = current_counts.copy()
    
    for _ in range(10):
        # Calculate deficits and pick highest
        deficits = []
        for area in distinct_areas:
            deficit = target_per_area - temp_counts[area]
            deficits.append((area, deficit))
        
        # Sort by deficit descending, add slight random shuffle to same-deficit areas
        random.shuffle(deficits)
        deficits.sort(key=lambda x: x[1], reverse=True)
        best_area = deficits[0][0]
        
        # Get candidate IDs for this SPECIFIC area
        area_candidates_query = """
            SELECT id FROM questions 
            WHERE category = :category 
            AND LOWER(area) = LOWER(:area)
            AND (LOWER(branch) = LOWER(:branch) OR FIND_IN_SET(LOWER(:branch), REPLACE(LOWER(branch), ' ', '')) OR :branch = 'COMMON')
        """
        area_candidates = [row[0] for row in db.execute(
            text(area_candidates_query),
            {"category": category.lower(), "area": best_area, "branch": branch_val}
        ).fetchall()]
        
        # Filter seen (avoiding repetition within the same daily quiz too)
        valid_candidates = [qid for qid in area_candidates if qid not in seen_ids and qid not in question_ids]
        
        selected_qid = None
        if valid_candidates:
            selected_qid = random.choice(valid_candidates)
        else:
            # Need more! Fallback: allow repeats if AI is disabled
            repeats = [qid for qid in area_candidates if qid not in question_ids]
            if repeats:
                selected_qid = random.choice(repeats)
        
        if selected_qid:
            question_ids.append(selected_qid)
            temp_counts[best_area] += 1
        else:
            # Absolute fallback: pick any available question from overall candidates
            remaining = [qid for qid in all_candidate_ids if qid not in question_ids]
            if remaining:
                pick = random.choice(remaining)
                question_ids.append(pick)

    # Truncate to 10 just in case
    question_ids = question_ids[:10]
    
    # Save for today (ONLY if NOT practice mode)
    if not is_practice_mode:
        db.execute(
            text("""
                INSERT INTO daily_quiz (username, category, quiz_date, question_ids)
                VALUES (:username, :category, :today, :ids)
                ON DUPLICATE KEY UPDATE question_ids = :ids
            """),
            {
                "username": username, 
                "category": category.lower(), 
                "today": today,
                "ids": ",".join(map(str, question_ids))
            }
        )
        db.commit()
    
    return question_ids

def get_questions_by_ids(db: Session, question_ids: list):
    """Fetch full question details"""
    placeholders = ",".join([str(id) for id in question_ids])
    
    result = db.execute(
        text(f"""
            SELECT id, question, option_a, option_b, option_c, option_d,
                   correct_answer, area, explanation, difficulty
            FROM questions 
            WHERE id IN ({placeholders})
        """)
    )
    
    rows = result.fetchall()
    
    # Map to dict for easy lookup
    questions_dict = {}
    for row in rows:
        ans = str(row[6]).strip().upper() if row[6] else "A"
        questions_dict[row[0]] = {
            "id": row[0],
            "question": row[1],
            "options": [row[2], row[3], row[4], row[5]],
            "answer": ans, # Frontend expects 'answer'
            "correct_answer": ans,
            "area": row[7] or "General",
            "explanation": row[8] or "No explanation provided.",
            "difficulty": row[9]
        }



    
    # Return in original order
    return [questions_dict[id] for id in question_ids if id in questions_dict]

def generate_question_explanation(db: Session, question_id: int):
    """Generate and save an AI explanation using Groq (via ai_engine) if it's missing."""
    from ai_engine import enhance_question, parse_ai_response
    
    result = db.execute(
        text("SELECT question, option_a, option_b, option_c, option_d, correct_answer, explanation FROM questions WHERE id = :id"),
        {"id": question_id}
    )
    row = result.fetchone()
    if not row:
        return
    
    question_text, opt_a, opt_b, opt_c, opt_d, correct_answer_letter, current_exp = row
    
    # If explanation is missing or placeholder, generate a new one
    is_placeholder = (
        not current_exp or 
        len(current_exp.strip()) < 50 or
        current_exp == "No explanation provided." or 
        current_exp == "Explanation generation failed."
    )
    
    if is_placeholder:
        print(f"🤖 [Background] Generating AI explanation for Q{question_id} using Groq...")
        options_text = f"A: {opt_a}, B: {opt_b}, C: {opt_c}, D: {opt_d}"
        
        try:
            # Use ai_engine to get high-quality explanation
            raw_ai = enhance_question(question_id, question_text, options_text, correct_answer_letter)
            parsed = parse_ai_response(raw_ai)
            
            if parsed and parsed.get("explanation"):
                new_explanation = parsed["explanation"]
                db.execute(
                    text("""
                        UPDATE questions 
                        SET explanation = :exp, area = :area, difficulty_level = :dl, difficulty = :dt 
                        WHERE id = :id
                    """),
                    {
                        "exp": new_explanation, 
                        "area": parsed["area"],
                        "dl": parsed["difficulty_level"],
                        "dt": parsed["difficulty_text"],
                        "id": question_id
                    }
                )
                db.commit()
                print(f"✅ [Background] Saved Groq explanation for Q{question_id}")
        except Exception as e:
            print(f"⚠️ [Background] Groq failed for Q{question_id}: {e}")

def ensure_explanations_exist(question_ids: list):
    """Ensure all questions in the list have AI explanations in parallel (Background Task)."""
    def job(qid):
        db = SessionLocal()
        try:
            generate_question_explanation(db, qid)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(job, question_ids)

def validate_answer(db: Session, question_id: int, user_answer: str):
    """
    Validate user answer and return explanation.
    """
    result = db.execute(
        text("SELECT correct_answer, explanation FROM questions WHERE id = :id"),
        {"id": question_id}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    
    correct_answer_letter, current_exp = row
    correct_answer_letter = correct_answer_letter.strip().upper()
    
    # If it's missing or clearly too short/placeholder, generate on the fly
    is_placeholder = (
        not current_exp or 
        len(current_exp.strip()) < 50 or
        current_exp == "No explanation provided." or 
        current_exp == "Explanation generation failed."
    )
    
    if is_placeholder:
        print(f"🤖 [Auto-Refining] Triggering explanation generation for Q{question_id}")
        generate_question_explanation(db, question_id)
        # Fetch updated explanation
        result = db.execute(text("SELECT explanation FROM questions WHERE id = :id"), {"id": question_id})
        current_exp = result.fetchone()[0]

    user_answer = user_answer.strip().upper()
    is_correct = (user_answer == correct_answer_letter)
    
    return is_correct, correct_answer_letter, current_exp or "No explanation provided."

# --- FASTAPI SETUP ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*70)
    print("PLACEMENT APP - STARTING UP")
    print("="*70)
    
    try:
        with engine.connect() as conn:
            print("Database connection successful!")
        
        # Initialize DB tables
        init_db()
        print("Database tables initialized")

        # Initialize Whisper model
        print("Loading Whisper model...")
        global stt_model
        stt_model = whisper.load_model("base")
        print("Whisper model loaded!")
        
    except Exception as e:
        print(f"Startup Failed: {e}")
        traceback.print_exc()
        raise e
    
    print("\nFeatures enabled:")
    print("   - Adaptive Quiz System (10 questions/day)")
    print("   - Progressive Difficulty")
    print("   - Interview Practice")
    print("   - Performance Analytics")
    
    print("\nAPI Documentation:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")
    
    yield
    
    print("\nShutting down gracefully...")

app = FastAPI(
    title="Placement Preparation Platform",
    description="AI-Powered Placement Prep with Adaptive Quiz System",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Import and include routers
from teacher_routes import router as teacher_router
from gd import router as gd_router
from news_routes import router as news_router

app.include_router(teacher_router)
app.include_router(gd_router, prefix="/gd_module", tags=["GD Module"])
app.include_router(news_router)

# --- ROUTES ---

@app.post("/register", tags=["Authentication"])
async def register(user: UserAuth, db: Session = Depends(get_db)):
    """Register a new user"""
    from models import User
    try:
        existing = db.query(User).filter(User.username == user.username.strip()).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Explicitly assign branch and other fields
        new_user = User()
        new_user.username = user.username.strip()
        new_user.password_hash = user.password
        new_user.aptitude_level = 1
        new_user.technical_level = 1
        new_user.branch = user.branch
        new_user.role = user.role.lower() if user.role else 'student'
        
        db.add(new_user)
        db.commit()
        return {"status": "success", "message": "User registered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login", tags=["Authentication"])
async def login(user: UserAuth, db: Session = Depends(get_db)):
    """Login user"""
    try:
        result = db.execute(
            text("SELECT username, password_hash FROM users WHERE username = :username"),
            {"username": user.username.strip()}
        )
        row = result.fetchone()
        
        if row and row[1] == user.password:
            # Trigger weekly level up check on login
            process_weekly_level_up(user.username.strip(), db)
            return {"status": "success", "username": row[0]}
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_branch", tags=["User"])
async def update_branch(request: UpdateBranchRequest, db: Session = Depends(get_db)):
    """Update user's branch after registration"""
    from models import User
    try:
        user = db.query(User).filter(User.username == request.username.strip()).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.branch = request.branch
        
        # Clear technical quiz cache for this user so they get correct branch questions immediately
        print(f"🗑️ Clearing technical quiz cache for user: {request.username.strip()}")
        result = db.execute(
            text("DELETE FROM daily_quiz WHERE username = :username AND category = 'technical'"),
            {"username": request.username.strip()}
        )
        print(f"✅ Cache cleared. Rows affected: {result.rowcount}")
        
        db.commit()
        return {"status": "success", "message": f"Branch updated to {request.branch}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_daily_quiz", tags=["Quiz System"])
async def get_daily_quiz(request: QuizRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Get today's 10 questions
    - Same questions for entire day
    - Resets at midnight
    """
    try:
        question_ids = get_todays_questions(db, request.username, request.category, request.target_branch)
        
        # Proactively generate explanations for any questions that lack them
        background_tasks.add_task(ensure_explanations_exist, question_ids)
        
        questions = get_questions_by_ids(db, question_ids)
        
        # Send full details to frontend
        
        return {
            "status": "success",
            "date": str(date.today()),
            "difficulty": get_user_level(db, request.username, request.category),
            "questions": questions,
            "total": len(questions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check_answer", tags=["Quiz System"])
async def check_answer(submission: AnswerSubmission, db: Session = Depends(get_db)):
    """Check a single answer - returns immediate feedback"""
    try:
        is_correct, correct_answer, explanation = validate_answer(
            db, 
            submission.question_id, 
            submission.user_answer
        )
        
        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "user_answer": submission.user_answer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_quiz", tags=["Quiz System"])
async def submit_quiz(submission: QuizCompleteSubmission, db: Session = Depends(get_db)):
    """
    Submit completed quiz
    - Updates user level if score >= 70%
    """
    try:
        percentage = (submission.score / submission.total_questions) * 100
        
        # Determine if this is practice mode
        user_result = db.execute(
            text("SELECT branch FROM users WHERE username = :username"),
            {"username": submission.username}
        )
        user_row = user_result.fetchone()
        user_branch = user_row[0] if user_row else None
        
        is_practice_mode = False
        if submission.target_branch and submission.target_branch != user_branch and submission.category.upper() == "TECHNICAL":
            is_practice_mode = True
            print(f"🎯 Practice Mode Submission: Score not saved for {submission.username}")
        
        # Save result (ONLY if NOT practice mode)
        if not is_practice_mode:
            # Use provided weak area or default to "Daily Quiz"
            area_to_save = submission.weak_area if submission.weak_area else "Daily Quiz"
            
            db.execute(
                text("""
                    INSERT INTO results (username, category, score, total_questions, area, timestamp) 
                    VALUES (:username, :category, :score, :total_questions, :area, NOW())
                """),
                {
                    "username": submission.username,
                    "category": submission.category.upper(),
                    "score": submission.score,
                    "total_questions": submission.total_questions,
                    "area": area_to_save
                }
            )
            
            # Level up logic removed from here (now weekly on Sundays)
            # Threshold was 70%, but we aggregate holistically now.
            level_up = False 
            
            db.commit()

            
            return {
                "status": "success",
                "score": submission.score,
                "total": submission.total_questions,
                "percentage": round(percentage, 1),
                "level_up": level_up,
                "message": "Great job! Level up!" if level_up else "Keep practicing!"
            }
        else:
             return {
                "status": "success",
                "score": submission.score,
                "total": submission.total_questions,
                "percentage": round(percentage, 1),
                "level_up": False,
                "message": f"Practice complete for {submission.target_branch}!"
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quiz_status/{username}/{category}", tags=["Quiz System"])
async def get_quiz_status(username: str, category: str, db: Session = Depends(get_db)):
    """Check if user has already taken today's quiz"""
    try:
        today = date.today()
        
        result = db.execute(
            text("""
                SELECT question_ids FROM daily_quiz 
                WHERE username = :username 
                AND category = :category 
                AND quiz_date = :today
            """),
            {"username": username, "category": category.lower(), "today": today}
        )
        
        existing = result.fetchone()
        has_quiz_today = existing is not None
        
        return {
            "has_quiz_today": has_quiz_today,
            "current_level": difficulty,
            "date": str(today)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weekly_report/{username}", tags=["Analytics"])
async def get_weekly_report(username: str, db: Session = Depends(get_db)):
    """Get performance analytics with daily and weekly aggregations"""
    try:
        # 1. Daily Aggregation for Aptitude and Technical combined (First attempt only)
        def get_daily_agg():
            res = db.execute(
                text("""
                    SELECT DATE(r.timestamp) as day, AVG(r.score) as avg_score
                    FROM results r
                    INNER JOIN (
                        SELECT MIN(timestamp) as first_time
                        FROM results
                        WHERE username = :username AND category IN ('APTITUDE', 'TECHNICAL')
                        AND timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                        GROUP BY DATE(timestamp), category
                    ) sub ON r.timestamp = sub.first_time
                    WHERE r.username = :username AND r.category IN ('APTITUDE', 'TECHNICAL')
                    GROUP BY DATE(r.timestamp)
                    ORDER BY day ASC
                """),
                {"username": username.strip()}
            )
            return [{"score": round(float(r[1]), 1), "time": str(r[0])} for r in res.fetchall()]

        # 2. Weekly Aggregation for GD and Interview (Last 4 Weeks)
        def get_weekly_agg(cat_name):
            res = db.execute(
                text("""
                    SELECT YEARWEEK(timestamp) as week, AVG(score) as avg_score, MIN(DATE(timestamp)) as week_start
                    FROM results 
                    WHERE username = :username AND category = :category
                    AND timestamp >= DATE_SUB(CURDATE(), INTERVAL 4 WEEK)
                    GROUP BY YEARWEEK(timestamp)
                    ORDER BY week ASC
                """),
                {"username": username.strip(), "category": cat_name}
            )
            return [{"score": round(float(r[1]), 1), "week_start": str(r[2])} for r in res.fetchall()]

        # 2b. Cumulative Weekly Growth (Sum of first attempts for all 4 categories)
        def get_cumulative_weekly():
            res = db.execute(
                text("""
                    SELECT YEARWEEK(r.timestamp) as week, SUM(r.score) as total_score, MIN(DATE(r.timestamp)) as week_start
                    FROM results r
                    INNER JOIN (
                        SELECT MIN(timestamp) as first_time
                        FROM results
                        WHERE username = :username AND category IN ('APTITUDE', 'TECHNICAL', 'GD', 'INTERVIEW')
                        GROUP BY DATE(timestamp), category
                    ) sub ON r.timestamp = sub.first_time
                    WHERE r.username = :username
                    GROUP BY YEARWEEK(r.timestamp)
                    ORDER BY week ASC
                """),
                {"username": username.strip()}
            )
            return [{"score": int(r[1]), "week_start": str(r[2])} for r in res.fetchall()]

        overall_daily = get_daily_agg()
        gd_weekly = get_weekly_agg("GD")
        interview_weekly = get_weekly_agg("INTERVIEW")
        cumulative_weekly = get_cumulative_weekly()

        # 3. Consistency Streak
        streak_query = db.execute(
            text("SELECT DISTINCT DATE(timestamp) as d FROM results WHERE username = :username ORDER BY d DESC"),
            {"username": username.strip()}
        ).fetchall()
        dates = [r[0] for r in streak_query]
        streak = 0
        curr = date.today()
        if dates and curr not in dates and (curr - timedelta(days=1)) in dates:
            curr -= timedelta(days=1)
        while curr in dates:
            streak += 1
            curr -= timedelta(days=1)

        # 4. Strong Areas (Avg > 7.0)
        strong_res = db.execute(
            text("""
                SELECT area, AVG(score) as avg_s, COUNT(*) as count 
                FROM results 
                WHERE username = :username AND area IS NOT NULL AND area != '' AND area != 'Daily Quiz'
                GROUP BY area
            """),
            {"username": username.strip()}
        ).fetchall()
        
        strong_areas = [r[0] for r in strong_res if r[1] >= 7.0]
        
        # 5. Badges Logic
        badges = []
        # Topic Mastery (90% + min 5 attempts)
        for r in strong_res:
            if r[1] >= 9.0 and r[2] >= 5:
                badges.append({"name": f"{r[0]} Master", "icon": "emoji_events", "color": "gold"})
        
        # Consistency Badge
        if streak >= 7:
            badges.append({"name": "7-Day Streak", "icon": "whatshot", "color": "orange"})
            
        # GD Eloquent (Avg communication > 8.0 + min 3 sessions)
        gd_res = db.execute(
            text("SELECT AVG(communication_score), COUNT(*) FROM gd_evaluations WHERE username = :u"),
            {"u": username.strip()}
        ).fetchone()
        if gd_res and gd_res[0] and gd_res[0] >= 8.0 and gd_res[1] >= 3:
            badges.append({"name": "GD Eloquent", "icon": "record_voice_over", "color": "blue"})
            
        # Interview Ace (Avg overall > 8.5 + min 3 sessions)
        int_res = db.execute(
            text("SELECT AVG(score), COUNT(*) FROM results WHERE username = :u AND category = 'INTERVIEW'"),
            {"u": username.strip()}
        ).fetchone()
        if int_res and int_res[0] and int_res[0] >= 8.5 and int_res[1] >= 3:
            badges.append({"name": "Interview Ace", "icon": "work", "color": "purple"})

        # 6. Branch Rank Calculation
        # To determine rank, we fetch the branch leaderboard and find this user's position
        user_res = db.execute(
            text("SELECT branch FROM users WHERE username = :username"),
            {"username": username.strip()}
        ).fetchone()
        branch_rank = 0
        if user_res and user_res[0]:
            user_branch = user_res[0]
            # Fast inline fetch of leaderboard logic for rank calculation
            all_users = db.execute(
                text("SELECT username FROM users WHERE branch = :b AND role = 'student'"),
                {"b": user_branch}
            ).fetchall()
            
            ranks = []
            for u_row in all_users:
                uname = u_row[0]
                u_streak = 0
                u_curr = date.today()
                while True:
                    cnt = db.execute(
                        text("SELECT COUNT(*) FROM results WHERE username = :u AND DATE(timestamp) = :d"),
                        {"u": uname, "d": u_curr}
                    ).fetchone()[0]
                    if cnt > 0:
                        u_streak += 1
                        u_curr -= timedelta(days=1)
                    else:
                        break
                
                u_avg_res = db.execute(
                    text("SELECT AVG(score) FROM results WHERE username = :u AND timestamp >= DATE_SUB(Now(), INTERVAL 7 DAY)"),
                    {"u": uname}
                ).scalar()
                u_latest_avg = float(u_avg_res or 0)
                
                # Fetch retries for penalty correctly
                totals_res = db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_attempts,
                            COUNT(DISTINCT DATE(timestamp)) as unique_days
                        FROM results 
                        WHERE username = :u AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    """),
                    {"u": uname}
                ).fetchone()
                
                unq_days = totals_res[1] or 0
                tot_att = totals_res[0] or 0
                retries = max(0, tot_att - unq_days)
                
                # Formula with penalty
                u_readiness = max(0, min(100, (u_latest_avg * 8.5) + (min(u_streak, 7) * 2.1) - (retries * 0.5)))
                ranks.append((uname, u_readiness))
            
            ranks.sort(key=lambda x: x[1], reverse=True)
            for idx, (ranked_uname, _) in enumerate(ranks):
                if ranked_uname.lower() == username.strip().lower():
                    branch_rank = idx + 1
                    break
            badges.append({"name": "Interview Ace", "icon": "face", "color": "purple"})

        # 6. Calculate status and Readiness
        avg_res = db.execute(
            text("""
                SELECT AVG(score) FROM results 
                WHERE username = :username AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """),
            {"username": username.strip()}
        )
        latest_avg = float(avg_res.scalar() or 0)
        
        # Readiness Score: (avg_score * 8) + (streak * 2) - capped at 100
        readiness_score = min(100, (latest_avg * 8.5) + (min(streak, 7) * 2.1))

        status = "Beginner"
        if latest_avg >= 8: status = "Expert"
        elif latest_avg >= 5: status = "Intermediate"

        return {
            "has_data": any([overall_daily, gd_weekly, interview_weekly]),
            "overall_daily": overall_daily,
            "gd_weekly": gd_weekly,
            "interview_weekly": interview_weekly,
            "cumulative_weekly": cumulative_weekly,
            "status": status,
            "current_performance": round(latest_avg, 1),
            "streak": streak,
            "strong_areas": strong_areas,
            "readiness_score": round(readiness_score, 1),
            "badges": badges,
            "streak": streak,
            "branch_rank": branch_rank
        }
    except Exception as e:
        print(f"Error in weekly_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leaderboard/{branch}", tags=["Leaderboard"])
async def get_branch_leaderboard(branch: str, db: Session = Depends(get_db)):
    """Fetch top 10 students in a branch based on Readiness Score"""
    try:
        # 1. Get all students in this branch
        users = db.execute(
            text("SELECT username, aptitude_level, technical_level FROM users WHERE branch = :b AND role = 'student'"),
            {"b": branch}
        ).fetchall()

        leaderboard = []
        today = date.today()

        for user in users:
            uname = user[0]
            
            # 2. Calculate Streak (Past 7 days)
            streak = 0
            curr = today
            while True:
                count = db.execute(
                    text("SELECT COUNT(*) FROM results WHERE username = :u AND DATE(timestamp) = :d"),
                    {"u": uname, "d": curr}
                ).fetchone()[0]
                if count > 0:
                    streak += 1
                    curr -= timedelta(days=1)
                else:
                    break
            
            # 3. Calculate Latest Avg
            avg_res = db.execute(
                text("""
                    SELECT AVG(score) FROM results 
                    WHERE username = :u AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                """),
                {"u": uname}
            ).scalar()
            latest_avg = float(avg_res or 0)

            # 3b. Calculate Penalty for Multiple Attempts (Retries)
            totals_res = db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_attempts,
                        COUNT(DISTINCT DATE(timestamp)) as unique_days
                    FROM results 
                    WHERE username = :u AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                """),
                {"u": uname}
            ).fetchone()
            
            unique_days = totals_res[1] or 0
            total_attempts = totals_res[0] or 0
            retries = max(0, total_attempts - unique_days)

            # 4. Final Readiness Score = Base - Retry Penalty
            readiness = min(100, (latest_avg * 8.5) + (min(streak, 7) * 2.1))
            readiness = max(0, readiness - (retries * 0.5))
            
            # 5. Get Badges Count
            badges_count = db.execute(
                text("SELECT COUNT(*) FROM results WHERE username = :u AND score >= 9"),
                {"u": uname}
            ).fetchone()[0] or 0

            leaderboard.append({
                "username": uname,
                "readiness_score": round(readiness, 1),
                "badges_count": badges_count,
                "level": user[2] # Technical level as proxy for expertise
            })

        # Sort by readiness score descending
        leaderboard.sort(key=lambda x: x['readiness_score'], reverse=True)
        
        return leaderboard[:10] # Return Top 10

    except Exception as e:
        print(f"LEADERBOARD ERROR: {e}")
        return []


@app.get("/dashboard/{username}", tags=["User"])
async def get_dashboard(username: str, db: Session = Depends(get_db)):
    """Get user dashboard data with task tracking and weekly progress"""
    from models import User, Score
    try:
        user = db.query(User).filter(User.username == username.strip()).first()
        if not user:
            raise HTTPException(status_code=404, detail="User find failed")

        # Trigger weekly checks
        process_weekly_level_up(username.strip(), db)
        
        # 1. Check Daily Completions (Scores recorded TODAY)
        today = date.today()
        daily_res = db.execute(
            text("""
                SELECT category, SUM(score) as total_s, COUNT(*) as count 
                FROM results 
                WHERE username = :username AND DATE(timestamp) = :today
                GROUP BY category
            """),
            {"username": username.strip(), "today": today}
        ).fetchall()
        
        daily_stats = {row[0].upper(): row[2] for row in daily_res}
        # Assuming each 'result' entry for Apt/Tech represents 1 session of 10 questions
        aptitude_done = daily_stats.get("APTITUDE", 0) >= 1
        tech_done = daily_stats.get("TECHNICAL", 0) >= 1

        # 2. Check Weekly Completions (Strict CURRENT WEEK: Monday to Sunday)
        # Monday of this week: DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
        weekly_res = db.execute(
            text("""
                SELECT category, COUNT(*) as count 
                FROM results 
                WHERE username = :username 
                AND timestamp >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
                GROUP BY category
            """),
            {"username": username.strip()}
        ).fetchall()
        
        weekly_stats = {row[0].upper(): row[1] for row in weekly_res}
        gd_done = weekly_stats.get("GD", 0) >= 1
        interview_done = weekly_stats.get("INTERVIEW", 0) >= 1

        # 2. Count distinct days for each category this week
        tech_days = db.execute(text("""
            SELECT COUNT(DISTINCT DATE(timestamp)) FROM results 
            WHERE username = :username AND category = 'TECHNICAL'
            AND timestamp >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
        """), {"username": username.strip()}).fetchone()[0] or 0
        
        apt_days = db.execute(text("""
            SELECT COUNT(DISTINCT DATE(timestamp)) FROM results 
            WHERE username = :username AND category = 'APTITUDE'
            AND timestamp >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
        """), {"username": username.strip()}).fetchone()[0] or 0

        # 3. Calculate Weekly Progress (%)
        # Logic: 7 units for Tech + 7 units for Aptitude + 1 unit for GD + 1 unit for Interview = 16 units total
        progress_units = min(tech_days, 7) + min(apt_days, 7) + (1 if gd_done else 0) + (1 if interview_done else 0)
        weekly_progress = (progress_units / 16.0) * 100

        # 4. Weak Areas logic
        def get_top_weak_areas(cat_name):
            # 1. Total Distinct Days Check
            distinct_days_res = db.execute(
                text("SELECT COUNT(DISTINCT DATE(timestamp)) FROM results WHERE username = :username"),
                {"username": username.strip()}
            ).fetchone()
            
            total_days = distinct_days_res[0] or 0
            
            # 2. Strict Rolling 7-Day Window
            rolling_window_start = "DATE_SUB(NOW(), INTERVAL 7 DAY)"
            
            # Identify weak areas based ONLY on the last 7 days
            res = db.execute(
                text(f"""
                    SELECT 
                        area, 
                        SUM(score) as correct, 
                        SUM(total_questions) as total,
                        (SUM(score) / SUM(total_questions) * 100) as percentage
                    FROM results 
                    WHERE username = :username AND category = :category 
                    AND area != 'Daily Quiz' AND area IS NOT NULL
                    AND timestamp >= {rolling_window_start}
                    GROUP BY area 
                    HAVING percentage <= 70.0
                    ORDER BY percentage ASC 
                    LIMIT 3
                """),
                {"username": username.strip(), "category": cat_name}
            ).fetchall()
            
            return {
                "areas": [
                    {
                        "area": r[0], 
                        "correct": int(r[1]),
                        "total": int(r[2]),
                        "wrong": int(r[2]) - int(r[1]),
                        "percentage": round(float(r[3]), 1)
                    } for r in res
                ],
                "total_days": total_days,
                "status": "active" if total_days >= 3 else "collecting"
            }

        weak_areas_tech_data = get_top_weak_areas("TECHNICAL")
        weak_areas_apt_data = get_top_weak_areas("APTITUDE")

        # 5. Accuracy & Total Attempts
        all_time_res = db.execute(
            text("SELECT COUNT(*), AVG(score) FROM results WHERE username = :username"),
            {"username": username.strip()}
        ).fetchone()
        
        total_attempts = all_time_res[0] or 0
        avg_score = float(all_time_res[1] or 0)
        accuracy = (avg_score / 10.0) * 100

        # 6. Recent Daily Performance (Strictly Current Week: Monday to Sunday)
        current_week_daily = {
            "aptitude": [],
            "technical": []
        }
        
        # Calculate most recent Monday
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        print(f"DEBUG: Fetching dashboard for {username} since {monday}")
        for cat in ["APTITUDE", "TECHNICAL"]:
            res = db.execute(
                text("""
                    SELECT DATE(timestamp) as day, AVG(score) as avg_score, DAYNAME(timestamp) as day_name
                    FROM results
                    WHERE username = :username AND category = :cat
                    AND timestamp >= :monday
                    GROUP BY DATE(timestamp)
                    ORDER BY day ASC
                """),
                {"username": username.strip(), "cat": cat, "monday": monday}
            ).fetchall()
            
            print(f"DEBUG: Found {len(res)} results for {cat}")
            
            current_week_daily[cat.lower()] = [
                {"day": str(row[0]), "score": float(row[1]), "day_name": (row[2] or "Day")[:3]} 
                for row in res
            ]

        return {
            "id": user.id,
            "username": user.username,
            "aptitude_level": user.aptitude_level,
            "technical_level": user.technical_level,
            "branch": user.branch,
            "weak_areas_tech": weak_areas_tech_data["areas"],
            "weak_areas_apt": weak_areas_apt_data["areas"],
            "weak_areas_tech_status": weak_areas_tech_data["status"],
            "weak_areas_apt_status": weak_areas_apt_data["status"],
            "total_days": weak_areas_tech_data["total_days"],
            "tasks": {
                "aptitude_done": aptitude_done,
                "tech_done": tech_done,
                "gd_done": gd_done,
                "interview_done": interview_done
            },
            "weekly_progress": round(weekly_progress, 1),
            "total_attempts": total_attempts,
            "accuracy": round(accuracy, 1),
            "current_week_daily": current_week_daily
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate_interview", tags=["Interview Practice"])
async def evaluate(audio: UploadFile = File(...), username: str = Form("Anonymous"), db: Session = Depends(get_db)):

    """Evaluate interview audio response"""
    temp_filename = f"temp_{audio.filename}"
    try:
        with open(temp_filename, "wb") as f:
            f.write(await audio.read())
        
        transcription_result = stt_model.transcribe(temp_filename)
        transcription = transcription_result.get("text", "").strip()

        prompt = f"""
System: You are a strict Technical Interviewer.
Candidate's Answer: "{transcription}"
Question: "Explain final vs const in Dart."

Evaluate strictly. Return ONLY JSON:
{{
  "score": "X/10",
  "feedback": "Direct, honest feedback.",
  "ideal_answer": "Professional explanation."
}}
"""
        
        response = ollama.generate(model='llama3', prompt=prompt, format='json') 
        data = json.loads(response['response'])
        
        # Extract numeric score (e.g., "7/10" -> 7)
        score_val = 5 # default
        if 'score' in data:
            match = re.search(r'(\d+)', str(data['score']))
            if match:
                score_val = int(match.group(1))

        # Persist the score to the results table
        db.execute(
            text(
                """
                INSERT INTO results (username, score, total_questions, category, area, timestamp)
                VALUES (:username, :score, :total_questions, :category, :area, :timestamp)
                """
            ),
            {
                "username": username,
                "score": score_val,
                "total_questions": 1,
                "category": "INTERVIEW",
                "area": "Interview Practice", # Default area for interview
                "timestamp": datetime.now()
            }
        )
        db.commit()

        return {
            "status": "success",
            "score": data.get("score", "5/10"),
            "feedback": data.get("feedback", ""),
            "ideal_answer": data.get("ideal_answer", "")
        }

    except Exception as e:
        db.rollback() # Rollback in case of error during DB operation
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

import cv2
import numpy as np
from scipy.spatial import distance as dist

# --- GLOBAL SESSION STORAGE ---
session_answers = {}

# --- MEDIAPIPE INITIALIZATION ---
try:
    import mediapipe as mp
    from mediapipe.python.solutions import face_mesh as mp_face_mesh
    MEDIAPIPE_AVAILABLE = True
    test_mesh = mp_face_mesh.FaceMesh() 
except Exception as e:
    print(f"MediaPipe Load Error: {e}")
    MEDIAPIPE_AVAILABLE = False

# Indices for Behavioral Tracking
L_EYE = [362, 385, 387, 263, 373, 380]
R_EYE = [133, 158, 160, 33, 144, 153]
IRIS_CENTER = 468 

# --- BEHAVIORAL HELPERS ---
def get_ear(eye_points):
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])
    C = dist.euclidean(eye_points[0], eye_points[3])
    return (A + B) / (2.0 * C)

def analyze_video_session(video_path):
    if not MEDIAPIPE_AVAILABLE:
        return {"eye_contact": "N/A", "blinks_per_min": 0, "demeanor": "Unknown"}
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"eye_contact": "0%", "blinks_per_min": 0, "demeanor": "N/A"}

    face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
    total_frames, blink_count, contact_frames, consec_frames = 0, 0, 0, 0
    smile_frames = 0 
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        total_frames += 1
        
        # Optimize: Analyze every 10th frame (approx 3 FPS) for significantly faster feedback
        if total_frames % 10 != 0: continue 
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)
        
        if res.multi_face_landmarks:
            pts = res.multi_face_landmarks[0].landmark
            
            # 1. EAR for Blinks
            le = np.array([[pts[i].x, pts[i].y] for i in L_EYE])
            re = np.array([[pts[i].x, pts[i].y] for i in R_EYE])
            ear = (get_ear(le) + get_ear(re)) / 2.0
            if ear < 0.18: # Optimized threshold
                consec_frames += 1
            else:
                if consec_frames >= 2: blink_count += 1
                consec_frames = 0
            
            # 2. Gaze Tracking (0.35 - 0.65 for natural eye movement)
            iris = pts[IRIS_CENTER]
            ratio = (iris.x - pts[33].x) / (pts[133].x - pts[33].x)
            if 0.35 < ratio < 0.65: contact_frames += 1

            # 3. Basic Demeanor Tracking
            m_left, m_right = pts[61], pts[291]
            mouth_width = dist.euclidean([m_left.x, m_left.y], [m_right.x, m_right.y])
            if mouth_width > 0.07: smile_frames += 1
            
    cap.release()
    duration_min = (total_frames / 30) / 60
    
    demeanor = "Confident/Positive" if smile_frames > (total_frames * 0.1) else "Serious/Focused"
    if contact_frames < (total_frames * 0.3): demeanor = "Anxious/Distracted"

    return {
        "eye_contact": f"{round((contact_frames/max(1,total_frames))*100, 1)}%",
        "blinks_per_min": round(blink_count / max(0.1, duration_min), 1),
        "demeanor": demeanor
    }

# --- UPDATED: NON-MCQ QUESTION LOADER ---
import csv
import random

def load_questions_by_difficulty(filename, level):
    questions = []
    if not os.path.exists(filename): 
        return []
    try:
        with open(filename, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                # Use capitalized keys to match CSV headers
                q_text = row.get("Question", "").strip()
                if not q_text:
                    continue
                
                # Loose MCQ check: only skip if it explicitly mentions "following options" in text
                if "which of the following" in q_text.lower():
                    continue
                
                try: 
                    q_diff = int(row.get("Difficulty", 1))
                except: 
                    q_diff = 1
                    
                if q_diff == level:
                    questions.append({
                        "question": q_text,
                        "difficulty": q_diff,
                        "area": row.get("Area", "Technical"),
                        "ideal_answer": row.get("Answer", ""), 
                        "explanation": "Standard logic applies."
                    })
        return questions
    except Exception as e: 
        print(f"Error loading questions: {e}")
        return []

@app.get("/get_questions/{username}/{category}")
async def get_questions(username: str, category: str):
    db = SessionLocal()
    user = db.execute(
        text("SELECT * FROM users WHERE username=:u"), {"u": username.strip()}
    ).fetchone()
    db.close()
    
    cat = category.upper()
    level = getattr(user, "aptitude_level", 1) if cat == "APTITUDE" else getattr(user, "technical_level", 1) if user else 1
    
    # Constants for csv
    APTITUDE_CSV = "datasets/enhanced_clean_general_aptitude_dataset.csv"
    TECHNICAL_CSV = "datasets/enhanced_cse_dataset.csv"
    
    file = APTITUDE_CSV if cat == "APTITUDE" else TECHNICAL_CSV
    qs = load_questions_by_difficulty(file, level)
    if len(qs) < 5: 
        qs = load_questions_by_difficulty(file, 1) + load_questions_by_difficulty(file, 2)
    random.shuffle(qs)
    return {"questions": qs[:5], "level": level} # Optimized to 5 high-quality questions

# --- UPDATED: INTERVIEW EVALUATION ---

@app.post("/process_frame")
async def process_frame(username: str = Form(...), frame: UploadFile = File(...)):
    if not MEDIAPIPE_AVAILABLE:
        return {"warning": ""}
        
    temp_path = f"frame_{username}.jpg"
    content = await frame.read()
    with open(temp_path, "wb") as f:
        f.write(content)
        
    try:
        img = cv2.imread(temp_path)
        if img is None:
            return {"warning": "FACE_NOT_DETECTED"}
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # Use a single face mesh instance for efficiency
        face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
        res = face_mesh.process(img_rgb)
        
        if not res.multi_face_landmarks:
            return {"warning": "FACE_NOT_DETECTED"}
            
        pts = res.multi_face_landmarks[0].landmark
        
        # 1. Out of Box (Checking if nose is centered)
        nose = pts[1]
        if nose.x < 0.15 or nose.x > 0.85 or nose.y < 0.15 or nose.y > 0.85:
            return {"warning": "OUT_OF_BOX"}
            
        # 2. Eye Gaze 
        iris = pts[IRIS_CENTER]
        # Corner of eye reference
        eye_left = pts[33].x
        eye_right = pts[133].x
        if (eye_right - eye_left) > 0:
            ratio = (iris.x - eye_left) / (eye_right - eye_left)
            if ratio < 0.3 or ratio > 0.7:
                return {"warning": "EYE_GAZE"}
            
        return {"warning": ""}
    except Exception as e:
        print(f"Error processing frame: {e}")
        return {"warning": ""}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/evaluate_step")
async def evaluate_step(username: str = Form(...), question: str = Form(...), index: int = Form(...), audio: UploadFile = File(...)):
    a_path = f"temp_{username}_{index}.m4a"
    with open(a_path, "wb") as f: 
        f.write(await audio.read())
    
    # IMPROVED: Voice Recognition context to prevent "Roman Y" errors
    result = stt_model.transcribe(a_path, language="en", task="transcribe", initial_prompt="This is a technical interview in English.")
    transcription = result["text"]
    
    if username not in session_answers:
        session_answers[username] = []
    
    session_answers[username].append({"question": question, "answer": transcription})
    os.remove(a_path)
    return {"status": "recorded", "index": index, "preview": transcription[:50]}

@app.post("/final_session_report")
async def final_session_report(username: str = Form(...), video: Optional[UploadFile] = File(None)):
    v_path = f"v_{username}.mp4"
    if video:
        with open(v_path, "wb") as f: f.write(await video.read())
        behavior_metrics = analyze_video_session(v_path)
    else:
        behavior_metrics = {"eye_contact": "N/A", "blinks_per_min": 0, "demeanor": "N/A (No Video Provided)"}

    
    qa_history = session_answers.get(username, [])
    qa_text = ""
    for item in qa_history:
        ans = item['answer'] if len(item['answer']) > 3 else "No audible response recorded."
        qa_text += f"Question: {item['question']}\\nCandidate Answer: {ans}\\n\\n"
    # STRICT: Mandatory Ideal Answers and Technical Grading
    prompt = f"""
    Evaluate this full technical interview session professionally. 
    BEHAVIORAL DATA: {behavior_metrics}
    FULL TRANSCRIPT:
    {qa_text}

    IMPORTANT: 
    1. If the 'Candidate Answer' is "No audible response", the score for that question is 0.
    2. Provide a professional 'ideal_answer' for every question.
    3. Be fair—if eye contact is 0%, mention it might be a camera glitch but advise the candidate.

    STRICTNESS RULES:
    1. If Eye Contact is < 50%, cap the 'overall_confidence' at 'Poor'.
    2. If the answer contains 'N/A' or is shorter than 10 words, score that question 0/10.
    3. Be critical of technical buzzwords used incorrectly.

    Return JSON with 'strict_critique' field.

    Format your response as a JSON object with this exact structure:
    {{
      "final_score": "Score/10",
      "overall_confidence": "Summary of behavior metrics.",
      "behavioral_feedback": "Concise critique of posture/eye contact.",
      "technical_report": [
         {{
           "question": "Original question",
           "your_answer": "Transcribed answer",
           "accuracy": "XX%", 
           "ideal_answer": "Key 1-sentence explanation",
           "improvement": "One missing keyword"
         }}
      ]
    }}
    """
    
    try:
        response = ollama.generate(model='llama3', prompt=prompt, format='json')
        report = json.loads(response['response'])
    except Exception as e:
        print(f"Ollama Error: {e}")
        # Fallback report if AI fails
        report = {
            "final_score": "7/10",
            "overall_confidence": "Technical session completed.",
            "behavioral_feedback": "Behavior metrics recorded.",
            "technical_report": [
                {
                    "question": item['question'],
                    "your_answer": item['answer'],
                    "accuracy": "70%",
                    "ideal_answer": "Evaluation pending AI analysis.",
                    "improvement": "Review technical keywords."
                } for item in qa_history
            ]
        }
    
    try:
        score_val = float(str(report.get("final_score", "0")).split("/")[0])
    except:
        score_val = 5.0


    # Inline DB write logic matching the rest of the application
    db = SessionLocal()
    try:
        db.execute(text(
            "INSERT INTO results (username, category, score, area, confidence) VALUES (:u, 'INTERVIEW', :s, 'Technical', :c)"
        ), {"u": username.strip(), "s": str(score_val), "c": str(behavior_metrics)})
        db.commit()
    except Exception as e:
        print(f"Error saving final interview report to db: {e}")
        db.rollback()
    finally:
        db.close()

    session_answers[username] = [] 
    if os.path.exists(v_path): os.remove(v_path)
    
    return report

@app.get("/", tags=["Root"])
def root():
    return {
        "app": "Placement Preparation Platform",
        "version": "4.0.0",
        "database": "MySQL",
        "features": {
            "adaptive_quiz": "10 questions daily with progressive difficulty",
            "answer_validation": "Fixed - accurate checking",
            "level_system": "Auto-level up at 70% score",
            "interview_practice": "Voice-based AI evaluation",
            "analytics": "Performance tracking"
        },
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)