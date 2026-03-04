import cv2
import subprocess
import json

def extract_frame(video_path):
    cap = cv2.VideoCapture(video_path)

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)

    success, frame = cap.read()
    cap.release()

    if not success:
        raise Exception("Could not read video")

    frame = cv2.resize(frame, (512,512))

    img_path = video_path + ".jpg"
    cv2.imwrite(img_path, frame)

    return img_path


def analyze_camera(video_path):

    img = extract_frame(video_path)

    prompt = """
Evaluate speaking confidence from 0–10 based on:

- eye contact
- posture
- facial confidence
- engagement

Return ONLY JSON:
{
 "camera_score": number,
 "camera_feedback": "text"
}
"""

    result = subprocess.run(
        ["ollama", "run", "llava", img],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=60
    )


    raw = result.stdout.strip()

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except:
        return {
            "camera_score": 5,
            "camera_feedback": "Could not analyze camera"
        }
