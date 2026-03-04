import json
import re
import subprocess
import librosa
from camera_eval import analyze_camera


# ---------------------------
# SILENCE DETECTION
# ---------------------------

def is_silent_audio(audio_path: str) -> bool:
    try:
        y, sr = librosa.load(audio_path, sr=None)
        intervals = librosa.effects.split(y, top_db=25)
        speech_time = sum((end - start) / sr for start, end in intervals)
        return speech_time < 1.0  # less than 1 sec speech = silent
    except Exception:
        return True


def is_silent_transcript(transcript: str) -> bool:
    if not transcript:
        return True
    words = transcript.strip().split()
    return len(words) < 3


# ---------------------------
# OLLAMA RUNNER
# ---------------------------

def run_ollama(prompt: str) -> str:
    process = subprocess.run(
        ["ollama", "run", "llama3:8b"],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
            errors="ignore",
    timeout=90
    )

    return process.stdout.strip()


# ---------------------------
# JSON EXTRACTION (ROBUST)
# ---------------------------

def extract_json(text: str) -> dict:
    text = text.strip()

    # find first { and last }
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found.\n{text}")

    json_str = text[start:end+1]

    try:
        return json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Invalid JSON:\n{json_str}") from e



# ---------------------------
# MAIN EVALUATION FUNCTION
# ---------------------------

def evaluate_gd(topic: str, transcript: str, audio_path: str, video_path: str) -> dict:
    """
    Central GD evaluation logic.
    ALL strictness and penalties handled here.
    """

    # ---------------------------
    # HARD FAIL: SILENCE
    # ---------------------------
    if is_silent_audio(audio_path) or is_silent_transcript(transcript):
        return {
            "transcript": transcript or "",
            "content_score": 0,
            "communication_score": 0,
            "camera_score": 0,
            "final_score": 0,
            "feedback": "No meaningful speech detected. Please speak clearly and stay on topic.",
            "camera_feedback": "No face detected or no speech.",
            "ideal_answer": ""
        }

    # ---------------------------
    # OLLAMA PROMPT
    # ---------------------------
    prompt = f"""
You are a strict Group Discussion evaluator.

Topic:
"{topic}"

User response:
"{transcript}"

Rules:
- Return ONLY valid JSON
- NO markdown
- NO explanations
- NO extra text

Scoring rules:
- Content score (0-10): relevance, depth, logic
- Communication score (0-10): fluency, clarity, confidence
- Penalize off-topic answers
- Penalize very short answers (<10 words)
- Be STRICT

Return format:
{{
  "content_score": <int>,
  "communication_score": <int>,
  "feedback": "<string>",
  "ideal_answer": "<string>"
}}
"""

    raw_output = run_ollama(prompt)

    # ---------------------------
    # PARSE JSON
    # ---------------------------
    try:
        result = extract_json(raw_output)
    except Exception as e:
        raise RuntimeError(
            f"Ollama returned invalid JSON.\nRaw output:\n{raw_output}"
        ) from e

    # ---------------------------
    # NORMALIZE SCORES
    # ---------------------------
    result["content_score"] = int(max(0, min(10, result.get("content_score", 0))))
    result["communication_score"] = int(max(0, min(10, result.get("communication_score", 0))))

    # ---------------------------
    # STRICT PENALTIES
    # ---------------------------
    word_count = len(transcript.split())

    # Very short answer → heavy penalty
    if word_count < 10:
        result["content_score"] = min(result["content_score"], 3)
        result["communication_score"] = min(result["communication_score"], 3)

    # Weak communication → cap content
    if result["communication_score"] <= 2:
        result["content_score"] = min(result["content_score"], 4)

    # ---------------------------
    # CAMERA ANALYSIS
    # ---------------------------
    try:
        camera = analyze_camera(video_path)
        camera_score = int(max(0, min(10, camera.get("camera_score", 5))))
        camera_feedback = camera.get("camera_feedback", "")
    except Exception:
        camera_score = 5
        camera_feedback = "Camera analysis failed."

    # ---------------------------
    # FINAL SCORE CALCULATION
    # ---------------------------
    final_score = round(
        result["content_score"] * 0.5 +
        result["communication_score"] * 0.3 +
        camera_score * 0.2
    )

    # ---------------------------
    # FINAL RESPONSE
    # ---------------------------
    print("OLLAMA RESULT:", result)

    return {
        "transcript": transcript,
        "content_score": result["content_score"],
        "communication_score": result["communication_score"],
        "camera_score": camera_score,
        "final_score": final_score,
        "feedback": result["feedback"],
        "camera_feedback": camera_feedback,
        "ideal_answer": result["ideal_answer"]
    }
