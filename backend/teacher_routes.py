"""
Teacher/Admin Routes for Student Monitoring
Provides endpoints for teachers to view student progress and analytics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date

from database import get_db

router = APIRouter(prefix="/teacher", tags=["teacher"])


class TeacherLogin(BaseModel):
    username: str
    password: str


@router.post("/login")
async def teacher_login(credentials: TeacherLogin, db: Session = Depends(get_db)):
    """
    Teacher login endpoint
    Validates credentials and checks role = 'teacher'
    """
    
    result = db.execute(
        text("SELECT username, role, branch FROM users WHERE username = :username AND password_hash = :password"),
        {"username": credentials.username, "password": credentials.password}
    )
    
    user = result.fetchone()
    
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    if user[1] != 'teacher':
        raise HTTPException(403, "Access denied - Teacher account required")
    
    return {
        "success": True,
        "username": user[0],
        "role": user[1],
        "branch": user[2],
        "message": "Teacher login successful"
    }


@router.get("/students")
async def get_all_students(branch: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get list of all students with basic info
    Optional filter by branch
    """
    
    query = """
        SELECT 
            u.username,
            u.branch,
            u.created_at,
            u.aptitude_level,
            u.technical_level,
            COUNT(DISTINCT r.id) as total_quizzes,
            MAX(dq.quiz_date) as last_quiz_date,
            AVG(r.score) as avg_score
        FROM users u
        LEFT JOIN results r ON u.username = r.username
        LEFT JOIN daily_quiz dq ON u.username = dq.username
        WHERE u.role = 'student'
    """
    
    if branch:
        query += " AND u.branch = :branch"
    
    query += """
        GROUP BY u.username, u.branch, u.created_at, u.aptitude_level, u.technical_level
        ORDER BY u.username
    """
    
    params = {"branch": branch} if branch else {}
    result = db.execute(text(query), params)
    
    students = []
    for row in result.fetchall():
        students.append({
            "username": row[0],
            "branch": row[1] or "Not Set",
            "joined_date": str(row[2]),
            "aptitude_level": row[3],
            "technical_level": row[4],
            "total_quizzes": row[5] or 0,
            "last_active": str(row[6]) if row[6] else "Never",
            "avg_score": round(row[7], 1) if row[7] else 0
        })
    
    return {
        "total_students": len(students),
        "branch_filter": branch or "All",
        "students": students
    }



@router.get("/students/{username}/progress")
async def get_student_progress(username: str, db: Session = Depends(get_db)):
    """
    Get detailed progress for a specific student
    """
    
    # Check if student exists
    user_result = db.execute(
        text("SELECT username, branch, created_at, aptitude_level, technical_level FROM users WHERE username = :username AND role = 'student'"),
        {"username": username}
    )
    user = user_result.fetchone()
    
    if not user:
        raise HTTPException(404, "Student not found")
    
    # Get quiz history
    quiz_history = db.execute(text("""
        SELECT 
            r.category,
            r.score,
            r.area,
            r.timestamp
        FROM results r
        WHERE r.username = :username
        ORDER BY r.timestamp DESC
        LIMIT 50
    """), {"username": username})
    
    history = []
    for row in quiz_history.fetchall():
        history.append({
            "category": row[0],
            "score": row[1],
            "total": 10,  # Assuming 10 questions per quiz
            "percentage": round(row[1] * 10, 1),  # score is already out of 10
            "area": row[2],
            "date": str(row[3])
        })
    
    # Get weak areas (areas with low scores) - rolling 7 days
    weak_areas = db.execute(text("""
        SELECT 
            area,
            (SUM(score) / SUM(total_questions) * 100) as avg_percentage,
            COUNT(*) as attempts
        FROM results
        WHERE username = :username 
          AND area IS NOT NULL 
          AND area != 'Daily Quiz'
          AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY area
        HAVING avg_percentage <= 70
        ORDER BY avg_percentage ASC
        LIMIT 5
    """), {"username": username})
    
    weak_areas_list = []
    for row in weak_areas.fetchall():
        weak_areas_list.append({
            "area": row[0],
            "avg_score": round(row[1], 1),
            "attempts": row[2]
        })
    
    # Get daily quiz completion streak
    today = date.today()
    streak_result = db.execute(text("""
        SELECT COUNT(DISTINCT quiz_date) as days_completed
        FROM daily_quiz
        WHERE username = :username
        AND quiz_date >= DATE_SUB(:today, INTERVAL 7 DAY)
    """), {"username": username, "today": today})
    
    days_completed = streak_result.scalar() or 0
    
    # Category-wise stats
    category_stats = db.execute(text("""
        SELECT 
            category,
            COUNT(*) as total_quizzes,
            AVG(score * 10) as avg_percentage,
            MAX(score * 10) as best_percentage
        FROM results
        WHERE username = :username
        GROUP BY category
    """), {"username": username})
    
    stats_by_category = {}
    for row in category_stats.fetchall():
        stats_by_category[row[0]] = {
            "total_quizzes": row[1],
            "avg_score": round(row[2], 1) if row[2] else 0,
            "best_score": round(row[3], 1) if row[3] else 0
        }
    
    return {
        "student": {
            "username": user[0],
            "branch": user[1] or "Not Set",
            "joined_date": str(user[2]),
            "aptitude_level": user[3],
            "technical_level": user[4]
        },
        "quiz_history": history,
        "weak_areas": weak_areas_list,
        "completion_last_7_days": days_completed,
        "category_stats": stats_by_category
    }


@router.get("/dashboard/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Get high-level dashboard statistics
    """
    
    # Total students
    total_students = db.execute(
        text("SELECT COUNT(*) FROM users WHERE role = 'student'")
    ).scalar() or 0
    
    # Active students (last 7 days)
    active_students = db.execute(text("""
        SELECT COUNT(DISTINCT username)
        FROM daily_quiz
        WHERE quiz_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    """)).scalar() or 0
    
    # Students by branch
    branch_dist_res = db.execute(text("""
        SELECT branch, COUNT(*) as count
        FROM users
        WHERE role = 'student' AND branch IS NOT NULL
        GROUP BY branch
        ORDER BY count DESC
    """))
    branch_distribution = {row[0]: row[1] for row in branch_dist_res.fetchall()}
    
    # Overall completion rate (7 days)
    completion_data = db.execute(text("""
        SELECT 
            (SELECT COUNT(*) FROM daily_quiz WHERE quiz_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) /
            (NULLIF((SELECT COUNT(*) FROM users WHERE role = 'student') * 7, 0)) * 100
    """)).scalar() or 0
    completion_rate = float(completion_data)

    # Today's stats
    today_stats = db.execute(text("""
        SELECT COUNT(DISTINCT username) FROM daily_quiz WHERE quiz_date = CURDATE()
    """)).scalar() or 0

    # At-Risk students (low avg score < 40% OR no activity in last 10 days)
    at_risk_count = db.execute(text("""
        SELECT COUNT(DISTINCT u.username)
        FROM users u
        LEFT JOIN results r ON u.username = r.username
        LEFT JOIN daily_quiz dq ON u.username = dq.username
        WHERE u.role = 'student'
        AND (
            (SELECT AVG(score * 10) FROM results WHERE username = u.username) < 40
            OR NOT EXISTS (SELECT 1 FROM daily_quiz WHERE username = u.username AND quiz_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY))
        )
    """)).scalar() or 0

    return {
        "total_students": total_students,
        "active_students_7d": active_students,
        "at_risk_count": at_risk_count,
        "branch_distribution": branch_distribution,
        "completion_rate_7d": round(completion_rate, 1),
        "today_activity": today_stats,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dashboard/batch_trends")
async def get_batch_trends(db: Session = Depends(get_db)):
    """
    Get 4-week historical trends for engagement and scores
    """
    trends = []
    for i in range(4):
        start_date = date.today() - timedelta(days=(i+1)*7)
        end_date = date.today() - timedelta(days=i*7)
        
        avg_score = db.execute(text("""
            SELECT AVG(score * 10) FROM results 
            WHERE timestamp BETWEEN :start AND :end
        """), {"start": start_date, "end": end_date}).scalar() or 0
        
        engagement = db.execute(text("""
            SELECT COUNT(DISTINCT username) FROM daily_quiz 
            WHERE quiz_date BETWEEN :start AND :end
        """), {"start": start_date, "end": end_date}).scalar() or 0
        
        trends.append({
            "week": f"Week {4-i}",
            "avg_score": round(avg_score, 1),
            "engagement": engagement
        })
    
    return {"trends": trends[::-1]} # Return chronological


@router.get("/dashboard/ai_recommendations")
async def get_ai_recommendations(db: Session = Depends(get_db)):
    """
    Get AI-generated suggestions for the teacher based on overall data
    """
    from ai_engine import call_groq
    
    # Gather summary data for the prompt
    # Get batch summary for context
    total_stats = await get_dashboard_overview(db)
    
    # Get worst performing category
    worst_cat_result = db.execute(text("""
        SELECT category, AVG(score * 10) as avg_p 
        FROM results 
        GROUP BY category ORDER BY avg_p ASC LIMIT 1
    """)).fetchone()
    
    worst_cat = worst_cat_result[0] if worst_cat_result else "None"
    
    prompt = f"""
    As an expert academic advisor, analyze this batch performance data and provide 3 actionable tips for the Placement Coordinator.
    
    Total Students: {total_stats['total_students']}
    7-Day Active: {total_stats['active_students_7d']}
    Completion Rate: {total_stats['completion_rate_7d']}%
    Weakest Module: {worst_cat}
    
    Provide tips in a clear list. Return ONLY the tips.
    """
    
    recommendation = call_groq(prompt, max_tokens=200) or "Continue monitoring student progress and encourage daily practice."
    
    return {"recommendation": recommendation}


@router.get("/dashboard/branch/{branch}")
async def get_branch_analytics(branch: str, db: Session = Depends(get_db)):
    """
    Get analytics for a specific branch
    """
    
    # Total students in branch
    total = db.execute(
        text("SELECT COUNT(*) FROM users WHERE role = 'student' AND branch = :branch"),
        {"branch": branch}
    ).scalar() or 0
    
    if total == 0:
        raise HTTPException(404, f"No students found in branch: {branch}")
    
    # Average scores by category
    avg_scores = db.execute(text("""
        SELECT 
            r.category,
            AVG(r.score * 10) as avg_percentage
        FROM results r
        JOIN users u ON r.username = u.username
        WHERE u.branch = :branch AND u.role = 'student'
        GROUP BY r.category
    """), {"branch": branch})
    
    category_averages = {}
    for row in avg_scores.fetchall():
        category_averages[row[0]] = round(row[1], 1) if row[1] else 0
    
    # Top performers (top 5)
    top_performers = db.execute(text("""
        SELECT 
            u.username,
            AVG(r.score * 10) as avg_percentage,
            COUNT(r.id) as total_quizzes
        FROM users u
        JOIN results r ON u.username = r.username
        WHERE u.branch = :branch AND u.role = 'student'
        GROUP BY u.username
        ORDER BY avg_percentage DESC
        LIMIT 5
    """), {"branch": branch})
    
    top_5 = []
    for row in top_performers.fetchall():
        top_5.append({
            "username": row[0],
            "avg_score": round(row[1], 1),
            "total_quizzes": row[2]
        })
    
    # Students needing attention (low scores or inactive)
    needs_attention = db.execute(text("""
        SELECT 
            u.username,
            AVG(r.score * 10) as avg_percentage,
            MAX(dq.quiz_date) as last_active
        FROM users u
        LEFT JOIN results r ON u.username = r.username
        LEFT JOIN daily_quiz dq ON u.username = dq.username
        WHERE u.branch = :branch AND u.role = 'student'
        GROUP BY u.username
        HAVING avg_percentage < 50 OR last_active < DATE_SUB(CURDATE(), INTERVAL 7 DAY) OR last_active IS NULL
        ORDER BY avg_percentage ASC
        LIMIT 10
    """), {"branch": branch})
    
    attention_list = []
    for row in needs_attention.fetchall():
        attention_list.append({
            "username": row[0],
            "avg_score": round(row[1], 1) if row[1] else 0,
            "last_active": str(row[2]) if row[2] else "Never"
        })
    
    return {
        "branch": branch,
        "total_students": total,
        "category_averages": category_averages,
        "top_performers": top_5,
        "needs_attention": attention_list
    }


@router.get("/dashboard/activity")
async def get_daily_activity(date_str: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get daily activity report
    date_str format: YYYY-MM-DD (defaults to today)
    """
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date.today()
    
    # Students who completed quizzes on target date
    completed = db.execute(text("""
        SELECT DISTINCT
            u.username,
            u.branch,
            GROUP_CONCAT(DISTINCT dq.category) as categories
        FROM users u
        JOIN daily_quiz dq ON u.username = dq.username
        WHERE u.role = 'student' AND dq.quiz_date = :target_date
        GROUP BY u.username, u.branch
        ORDER BY u.username
    """), {"target_date": target_date})
    
    completed_list = []
    for row in completed.fetchall():
        completed_list.append({
            "username": row[0],
            "branch": row[1] or "Not Set",
            "categories_completed": row[2].split(',') if row[2] else []
        })
    
    # Students who missed quizzes (registered but no activity on target date)
    missed = db.execute(text("""
        SELECT u.username, u.branch
        FROM users u
        WHERE u.role = 'student'
        AND u.username NOT IN (
            SELECT DISTINCT username
            FROM daily_quiz
            WHERE quiz_date = :target_date
        )
        AND u.created_at < :target_date
        ORDER BY u.username
    """), {"target_date": target_date})
    
    missed_list = []
    for row in missed.fetchall():
        missed_list.append({
            "username": row[0],
            "branch": row[1] or "Not Set"
        })
    
    # Category breakdown
    category_breakdown = db.execute(text("""
        SELECT category, COUNT(DISTINCT username) as count
        FROM daily_quiz
        WHERE quiz_date = :target_date
        GROUP BY category
    """), {"target_date": target_date})
    
    breakdown = {}
    for row in category_breakdown.fetchall():
        breakdown[row[0]] = row[1]
    
    return {
        "date": str(target_date),
        "students_completed": len(completed_list),
        "students_missed": len(missed_list),
        "completion_rate": round((len(completed_list) / (len(completed_list) + len(missed_list)) * 100), 1) if (len(completed_list) + len(missed_list)) > 0 else 0,
        "category_breakdown": breakdown,
        "completed_details": completed_list,
        "missed_details": missed_list
    }
