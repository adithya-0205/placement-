# AI Placement Assistant: Advanced Module Walkthrough

This document dives into the complex technical logic of the platform's most sophisticated features. These are the "power features" that will impress your evaluators.

---

## 🏎 1. Adaptive Quiz Engine (`backend/adaptive_quiz.py`)
This is the "Smart" part of your app. It ensures the difficulty adjusts to the student's level.

### The Algorithm:
*   **Performance Tracking**: The system calculates a rolling average of the student's last 50 questions across all categories.
*   **Sunday Level-Up**: A cron-style background task runs every Sunday. If a student's accuracy is > 75%, it updates their `technical_level` in the database.
*   **Query Weighting**: When fetching questions, the SQL query uses a `WEIGHTED RANDOM` approach. It prioritizes questions within the user's specific level but occasionally throws in one "Harder" question to test their growth.

---

## 🎤 2. GD & Interview AI Evaluation (`backend/gd_evaluator.py`)
How does the computer "grade" a human discussion?

### The Flow:
1.  **Audio In**: Flutter records a `.wav` file and sends it to the backend.
2.  **Transcription**: The backend uses **OpenAI Whisper (Local)** to convert speech to text.
3.  **Rubric-Based Prompting**: We don't just ask the AI "Is this good?". We send a specific Rubric:
    *   *Clarity*: Are the sentences structured well?
    *   *Confidence*: Does the user use filler words like "um" or "uh"? (Whisper detects these).
    *   *Domain knowledge*: Did the user mention specific technical keywords related to the topic?
4.  **Feedback Loop**: The AI returns a JSON score and 3 "Areas for Improvement."

---

## 🔐 3. Frontend State Management (`lib/providers/auth_provider.dart`)
How does the app "remember" you are logged in across different screens?

### The Logic:
*   **Provider Pattern**: We use the `Provider` library to wrap the entire app.
*   **LocalStorage (Persistence)**: When you log in, your Username and JWT (JSON Web Token) are saved to the device's persistent storage.
*   **notifyListeners()**: When the login status changes, this function is called. It tells every screen (Dashboard, Quiz, Profile) to "Re-draw" themselves with the new user data instantly, without a page reload.

---

## 👨‍🏫 4. Teacher/Admin Control Panel (`backend/teacher_routes.py`)
The system isn't just for students; it has a data-driven "Teacher Mode."

### Features:
*   **Class Metrics**: Teachers can see a leaderboard of their specific branch.
*   **Weakness Analysis**: The backend aggregates data to show a teacher: "70% of your class is struggling with 'LinkedLists'." This allows for data-driven teaching.
*   **Question Management**: Allows teachers to upload new CSV datasets directly into the MySQL database through a secure interface.

---

## 📊 5. Database Schema & Relationships (`backend/models.py`)
The "Blueprints" of your data.

### Key Tables:
*   `Students`: Tracks credentials, branch, and current difficulty level.
*   `Questions`: Contains 1000+ technical and aptitude items.
*   `UserProgress`: A junction table that records every single answer a student gives. This is what fuels the "Weekly Progress" graph.

---

### Pro-Tip for Evaluation:
When asked **"What was the hardest part?"**, you can say:
> "Ensuring the AI models (Whisper and Llama) ran efficiently on local hardware without lagging the frontend. We achieved this by pre-loading models into memory at server startup and using background processing for long tasks."
