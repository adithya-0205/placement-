# Quiz Deep Dive: Explanations, Difficulty, and Topics

This guide explains the "Smart Logic" behind how the system handles question difficulty, AI explanations, and identifying student weak areas.

---

## 💡 1. AI-Generated Explanations
Every question in the app comes with a detailed step-by-step explanation.

### How it works:
1.  **On-the-fly Generation**: When a student starts a quiz, the backend checks if the 10 questions have explanations. If any are missing, it triggers a **Background Task** (`ensure_explanations_exist` in `main.py`).
2.  **The AI Prompt**: We use **Llama 3.1** with this specific instruction:
    > "Act as a placement trainer. Provide a clear, step-by-step explanation for this question: [Question Content]. Keep it concise and professional."
3.  **Frontend Display**: In `quiz_screen.dart`, once you click an answer, the app reveals a "View Explanation" card. It uses the `explanation` field returned from our API to show the student *why* an answer is correct.

---

## 📈 2. Adaptive Difficulty Levels
The platform scales from **Easy (1)** to **Medium (2)** to **Hard (3)**.

### The Scaling Logic:
- **Starting Point**: Every new student starts at Level 1 (Easy).
- **The SQL Filter**: When fetching questions, the backend uses:
  ```sql
  SELECT * FROM questions WHERE branch = ? AND difficulty_level = ?
  ```
- **Weekly Auto-Promotion**: In `backend/main.py`, we have the `process_weekly_level_up` routine. 
  - Every Sunday, the system looks at the student's **Accuracy Rate** for the week.
  - **The Rule**: If accuracy is **> 75%**, the student's level is updated (+1). If it's **< 40%**, the level stays the same or can even decrease to ensure they master the basics first.

---

## 🎯 3. Area & Topic Detection (Weak Area Analysis)
How does the app know you are weak in "Data Structures"?

### The Data Flow:
1.  **Tagging**: Every question in our MySQL database has an `area` column (e.g., "Logical Reasoning", "Java", "Calculus").
2.  **Post-Quiz Submission**: When a student finishes a quiz, the backend doesn't just save the total score. It saves a record of every **Topic + Result** (Correct/Incorrect).
3.  **The Analytics Algorithm**: When you open the Dashboard, the backend performs a **Group By** calculation:
    ```sql
    SELECT area, count(*) as fails FROM user_progress 
    WHERE username = ? AND is_correct = 0 
    GROUP BY area ORDER BY fails DESC LIMIT 1
    ```
4.  **Result**: The topic with the most "Incorrect" answers is identified as the **Weak Area** and displayed on the student's dashboard with a red icon.

---

### Summary for Evaluators:
*   **Feature**: AI Explanations → **Benefit**: Instant clarification without a human teacher.
*   **Feature**: Adaptive Difficulty → **Benefit**: Personalized learning path (No one gets bored or overwhelmed).
*   **Feature**: Area Tracking → **Benefit**: Targeted practice where the student needs it most.
