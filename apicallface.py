# from fastapi import FastAPI, HTTPException
# from fastapi.responses import JSONResponse
# from typing import List, Optional, Literal
# from pydantic import Field
# import statistics
# import math
# import time
# import os
# from pydantic import BaseModel
# import random
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse 

# app = FastAPI(title="Mood & Heart Rate Analyzer API")
# # Static folder path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SONG_PATH = os.path.join(BASE_DIR, "static", "song.mp3")

# origins = ["*"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.get("/hello")
# async def stream_song():
#     if not os.path.exists(SONG_PATH):
#         return {"error": "Song not found"}

#     def iterfile():
#         with open(SONG_PATH, mode="rb") as file:
#             yield from file

#     return StreamingResponse(iterfile(), media_type="audio/mpeg")

# class TextInput(BaseModel):
#     text: str

# @app.post("/analyze")
# async def analyze_text(input_data: TextInput):
#     try:
#         bpm = 90 + random.randint(0, 30)  # Adds a small random offset to 90
#         response = {"mood": "neutral", "bpm": bpm}
#         return JSONResponse(content=response)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ----- Models -----
# class KeystrokeEvent(BaseModel):
#     key: Optional[str] = None
#     # timestamp in seconds (unix epoch float) or relative seconds
#     ts: float = Field(..., description="timestamp in seconds (float)")
#     # optional: 'down' or 'up' or omitted if only timestamps recorded
#     type: Optional[Literal['down', 'up']] = None

# class KeystrokePayload(BaseModel):
#     events: List[KeystrokeEvent]
#     meta: Optional[dict] = None  # optional metadata (user id, session id, etc.)

# # ----- Helpers -----
# def safe_mean(xs):
#     return statistics.mean(xs) if xs else 0.0

# def safe_std(xs):
#     return statistics.pstdev(xs) if len(xs) > 0 else 0.0

# def skewness(xs):
#     if len(xs) < 3: 
#         return 0.0
#     m = statistics.mean(xs)
#     s = statistics.pstdev(xs)
#     if s == 0: 
#         return 0.0
#     return sum(((x - m)/s)**3 for x in xs) / len(xs)

# def shannon_entropy(xs, bins=10):
#     if not xs:
#         return 0.0
#     mn, mx = min(xs), max(xs)
#     if mx == mn:
#         return 0.0
#     # histogram
#     bin_counts = [0]*bins
#     width = (mx - mn)/bins
#     for x in xs:
#         idx = int((x - mn) / width)
#         if idx == bins: idx = bins - 1
#         bin_counts[idx] += 1
#     total = len(xs)
#     entropy = 0.0
#     for c in bin_counts:
#         if c == 0: continue
#         p = c/total
#         entropy -= p * math.log2(p)
#     return entropy

# # ----- Feature extraction -----
# def extract_features(events):
#     if not events:
#         raise ValueError("No events supplied")

#     # sort by timestamp to be robust
#     events = sorted(events, key=lambda e: e.ts)

#     ts_list = [e.ts for e in events]
#     start_ts, end_ts = ts_list[0], ts_list[-1]
#     total_time = max(1e-6, end_ts - start_ts)  # avoid div by zero

#     # Count 'down' events as key presses; if no types provided, treat every event as a key press
#     down_events = [e for e in events if (e.type == 'down' or e.type is None)]
#     n_keys = len(down_events)

#     # Inter-key intervals (IKI) computed from consecutive down timestamps
#     down_ts = [e.ts for e in down_events]
#     ikis = [t2 - t1 for t1, t2 in zip(down_ts, down_ts[1:])] if len(down_ts) > 1 else []

#     # Hold times (key down -> key up) when both types are available
#     # Build map from key + occurrence index to pair down/up (best-effort)
#     hold_times = []
#     stack = []  # will store (key, ts) for down events
#     for e in events:
#         if e.type == 'down':
#             stack.append((e.key, e.ts))
#         elif e.type == 'up':
#             # pair with the last down of same key if available, else pair with last down
#             for i in range(len(stack)-1, -1, -1):
#                 if stack[i][0] == e.key:
#                     down_key, down_ts_val = stack.pop(i)
#                     hold_times.append(e.ts - down_ts_val)
#                     break
#             else:
#                 # fallback: pair with last down
#                 if stack:
#                     _, down_ts_val = stack.pop()
#                     hold_times.append(e.ts - down_ts_val)

#     # Correction/backspace statistics
#     backspace_count = sum(1 for e in down_events if (e.key and e.key.lower() in ('backspace', 'bksp', '⌫')))
#     delete_count = sum(1 for e in down_events if (e.key and e.key.lower() in ('delete',)))
#     correction_count = backspace_count + delete_count
#     correction_rate = correction_count / n_keys if n_keys else 0.0

#     # Pause metrics: define a long pause threshold (in seconds)
#     LONG_PAUSE_THRESH = 1.0
#     long_pauses = [x for x in ikis if x >= LONG_PAUSE_THRESH]
#     pause_count = len(long_pauses)
#     avg_long_pause = safe_mean(long_pauses) if long_pauses else 0.0

#     # Burstiness: coefficient of variation of IKI
#     mean_iki = safe_mean(ikis)
#     std_iki = safe_std(ikis)
#     burstiness = (std_iki / mean_iki) if mean_iki > 0 else 0.0

#     # Entropy of IKI distribution (higher => more irregular)
#     ikisent = shannon_entropy(ikis, bins=12)

#     # Derived rates
#     keys_per_sec = n_keys / total_time
#     keys_per_min = keys_per_sec * 60.0
#     typing_density = n_keys / (total_time + 1e-6)

#     features = {
#         "total_time_s": total_time,
#         "n_key_downs": n_keys,
#         "keys_per_sec": keys_per_sec,
#         "keys_per_min": keys_per_min,
#         "avg_iki_s": mean_iki,
#         "median_iki_s": statistics.median(ikis) if ikis else 0.0,
#         "std_iki_s": std_iki,
#         "min_iki_s": min(ikis) if ikis else 0.0,
#         "max_iki_s": max(ikis) if ikis else 0.0,
#         "burstiness": burstiness,
#         "iki_entropy": ikisent,
#         "hold_time_avg_s": safe_mean(hold_times),
#         "hold_time_std_s": safe_std(hold_times),
#         "n_hold_samples": len(hold_times),
#         "correction_count": correction_count,
#         "correction_rate": correction_rate,
#         "pause_count": pause_count,
#         "avg_long_pause_s": avg_long_pause,
#         "skewness_iki": skewness(ikis),
#     }

#     # Basic normalization (z-like) for a few features (minimally)
#     # Use simple transforms so downstream models get stable ranges
#     features["log_n_key_downs"] = math.log1p(features["n_key_downs"])
#     features["log_total_time_s"] = math.log1p(features["total_time_s"])

#     return features

# # ----- Heuristic mood mapping (explainable) -----
# def heuristic_mood(features):
#     """
#     Conservative, explainable heuristic. This is NOT a clinical model.
#     Returns a dict: {mood_label, score, reasons[]}
#     """
#     reasons = []
#     score = 0.0  # positive => more 'agitated', negative => more 'calm/relaxed'
#     kps = features.get("keys_per_sec", 0.0)
#     burst = features.get("burstiness", 0.0)
#     corr_rate = features.get("correction_rate", 0.0)
#     pause_count = features.get("pause_count", 0.0)
#     avg_hold = features.get("hold_time_avg_s", 0.0)

#     # heuristics
#     if kps > 5.0:
#         score += 1.2
#         reasons.append("High typing speed")
#     elif kps < 1.0:
#         score -= 0.8
#         reasons.append("Very slow typing")

#     if burst > 1.0:
#         score += 0.8
#         reasons.append("High burstiness (irregular rhythm)")

#     if corr_rate > 0.15:
#         score += 1.0
#         reasons.append("High correction rate (possible frustration)")

#     if pause_count >= 3:
#         score -= 0.6
#         reasons.append("Multiple long pauses (thinking/distracted)")

#     if avg_hold > 0.2:
#         # long key hold might indicate fatigue or slow typing -> calmer
#         score -= 0.4
#         reasons.append("Long average key hold time (slower/controlled)")

#     # map continuous score to mood
#     # score <= -0.5 -> relaxed / thoughtful
#     # -0.5 < score < 0.8 -> neutral / focused
#     # 0.8 <= score < 2.0 -> stressed / agitated
#     # >=2.0 -> highly agitated / upset
#     if score <= -0.5:
#         mood = "relaxed"
#         confidence = min(0.9, 1.0 - (score + 0.5))  # heuristic confidence
#     elif score < 0.8:
#         mood = "neutral/focused"
#         confidence = 0.6
#     elif score < 2.0:
#         mood = "stressed/agitated"
#         confidence = 0.7
#     else:
#         mood = "highly_agitated"
#         confidence = 0.8

#     return {"mood": mood, "score": round(score, 3), "confidence": round(confidence, 2), "reasons": reasons}

# # ----- Endpoint -----
# @app.post("/keystroke/analyze")
# async def analyze_keystrokes(payload: KeystrokePayload):
#     try:
#         if not payload.events or len(payload.events) < 2:
#             raise HTTPException(status_code=400, detail="Need at least 2 keystroke events")

#         features = extract_features(payload.events)
#         mood_est = heuristic_mood(features)

#         # Package response
#         response = {
#             "features": features,
#             "mood_estimate": mood_est,
#             "meta": payload.meta or {},
#             "generated_at": time.time()
#         }
#         return response
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional, Literal
from pydantic import Field
import statistics
import math
import time
import cv2
import numpy as np
import time
from deepface import DeepFace
from scipy.signal import find_peaks
from collections import Counter
import tempfile
import os
from pydantic import BaseModel
import random
import subprocess
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse 
app = FastAPI(title="Mood & Heart Rate Analyzer API")
# Static folder path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONG_PATH = os.path.join(BASE_DIR, "static", "song.mp3")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze-video/")
async def analyze_video(file: UploadFile = File(...)):
    # Validate input
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Invalid video format")

    # Save uploaded video temporarily
    temp_dir = tempfile.mkdtemp()
    temp_video_path = os.path.join(temp_dir, file.filename)
    with open(temp_video_path, "wb") as f:
        f.write(await file.read())

    # Re-encode with FFmpeg to standardize container, pixel format, and FPS
    reencoded_path = os.path.join(temp_dir, "reencoded.mp4")
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_video_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",  # standardize FPS
            reencoded_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg re-encoding failed: {str(e)}")

    try:
        # ---------- INITIALIZE ----------
        cap = cv2.VideoCapture(reencoded_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        green_intensity = []
        timestamps = []
        emotions = []
        bpm_values = []
        FRAME_WINDOW = 5

        start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_time = time.time() - start_time
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi = frame[y:y+h, x:x+w]

                # --- Emotion Detection ---
                try:
                    analysis = DeepFace.analyze(roi, actions=['emotion'], enforce_detection=False)
                    mood = analysis[0]['dominant_emotion']
                    emotions.append(mood)
                except Exception:
                    continue

                # --- Heart Rate (rPPG approximation) ---
                green_channel = np.mean(roi[:, :, 1])
                green_intensity.append(green_channel)
                timestamps.append(current_time)

                while timestamps and (timestamps[-1] - timestamps[0]) > FRAME_WINDOW:
                    timestamps.pop(0)
                    green_intensity.pop(0)

                if len(green_intensity) > 10:
                    signal = np.array(green_intensity) - np.mean(green_intensity)
                    peaks, _ = find_peaks(signal, distance=fps/2)
                    if len(peaks) > 1:
                        peak_intervals = np.diff(np.array(timestamps)[peaks])
                        bpm = 60 / np.mean(peak_intervals)
                        bpm_values.append(bpm)

        cap.release()

        # ---------- POST-PROCESS ----------
        most_common_emotion = Counter(emotions).most_common(1)[0][0] if emotions else "No Face"
        avg_bpm = float(np.mean(bpm_values)) if bpm_values else 0.0

        result = {
            "video_duration_sec": round(duration, 2),
            "most_frequent_emotion": most_common_emotion,
            "average_bpm": round(avg_bpm*4, 2)
        }
        print(result)
        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup
        for path in [temp_video_path, reencoded_path]:
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(temp_dir)

class TextInput(BaseModel):
    text: str

@app.post("/analyze")
async def analyze_text(input_data: TextInput):
    try:
        bpm = 90 + random.randint(0, 30)  # Adds a small random offset to 90
        response = {"mood": "neutral", "bpm": bpm}
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- Models -----
class KeystrokeEvent(BaseModel):
    key: Optional[str] = None
    # timestamp in seconds (unix epoch float) or relative seconds
    ts: float = Field(..., description="timestamp in seconds (float)")
    # optional: 'down' or 'up' or omitted if only timestamps recorded
    type: Optional[Literal['down', 'up']] = None

class KeystrokePayload(BaseModel):
    events: List[KeystrokeEvent]
    meta: Optional[dict] = None  # optional metadata (user id, session id, etc.)

# ----- Helpers -----
def safe_mean(xs):
    return statistics.mean(xs) if xs else 0.0

def safe_std(xs):
    return statistics.pstdev(xs) if len(xs) > 0 else 0.0

def skewness(xs):
    if len(xs) < 3: 
        return 0.0
    m = statistics.mean(xs)
    s = statistics.pstdev(xs)
    if s == 0: 
        return 0.0
    return sum(((x - m)/s)**3 for x in xs) / len(xs)

def shannon_entropy(xs, bins=10):
    if not xs:
        return 0.0
    mn, mx = min(xs), max(xs)
    if mx == mn:
        return 0.0
    # histogram
    bin_counts = [0]*bins
    width = (mx - mn)/bins
    for x in xs:
        idx = int((x - mn) / width)
        if idx == bins: idx = bins - 1
        bin_counts[idx] += 1
    total = len(xs)
    entropy = 0.0
    for c in bin_counts:
        if c == 0: continue
        p = c/total
        entropy -= p * math.log2(p)
    return entropy

# ----- Feature extraction -----
def extract_features(events):
    if not events:
        raise ValueError("No events supplied")

    # sort by timestamp to be robust
    events = sorted(events, key=lambda e: e.ts)

    ts_list = [e.ts for e in events]
    start_ts, end_ts = ts_list[0], ts_list[-1]
    total_time = max(1e-6, end_ts - start_ts)  # avoid div by zero

    # Count 'down' events as key presses; if no types provided, treat every event as a key press
    down_events = [e for e in events if (e.type == 'down' or e.type is None)]
    n_keys = len(down_events)

    # Inter-key intervals (IKI) computed from consecutive down timestamps
    down_ts = [e.ts for e in down_events]
    ikis = [t2 - t1 for t1, t2 in zip(down_ts, down_ts[1:])] if len(down_ts) > 1 else []

    # Hold times (key down -> key up) when both types are available
    # Build map from key + occurrence index to pair down/up (best-effort)
    hold_times = []
    stack = []  # will store (key, ts) for down events
    for e in events:
        if e.type == 'down':
            stack.append((e.key, e.ts))
        elif e.type == 'up':
            # pair with the last down of same key if available, else pair with last down
            for i in range(len(stack)-1, -1, -1):
                if stack[i][0] == e.key:
                    down_key, down_ts_val = stack.pop(i)
                    hold_times.append(e.ts - down_ts_val)
                    break
            else:
                # fallback: pair with last down
                if stack:
                    _, down_ts_val = stack.pop()
                    hold_times.append(e.ts - down_ts_val)

    # Correction/backspace statistics
    backspace_count = sum(1 for e in down_events if (e.key and e.key.lower() in ('backspace', 'bksp', '⌫')))
    delete_count = sum(1 for e in down_events if (e.key and e.key.lower() in ('delete',)))
    correction_count = backspace_count + delete_count
    correction_rate = correction_count / n_keys if n_keys else 0.0

    # Pause metrics: define a long pause threshold (in seconds)
    LONG_PAUSE_THRESH = 1.0
    long_pauses = [x for x in ikis if x >= LONG_PAUSE_THRESH]
    pause_count = len(long_pauses)
    avg_long_pause = safe_mean(long_pauses) if long_pauses else 0.0

    # Burstiness: coefficient of variation of IKI
    mean_iki = safe_mean(ikis)
    std_iki = safe_std(ikis)
    burstiness = (std_iki / mean_iki) if mean_iki > 0 else 0.0

    # Entropy of IKI distribution (higher => more irregular)
    ikisent = shannon_entropy(ikis, bins=12)

    # Derived rates
    keys_per_sec = n_keys / total_time
    keys_per_min = keys_per_sec * 60.0
    typing_density = n_keys / (total_time + 1e-6)

    features = {
        "total_time_s": total_time,
        "n_key_downs": n_keys,
        "keys_per_sec": keys_per_sec,
        "keys_per_min": keys_per_min,
        "avg_iki_s": mean_iki,
        "median_iki_s": statistics.median(ikis) if ikis else 0.0,
        "std_iki_s": std_iki,
        "min_iki_s": min(ikis) if ikis else 0.0,
        "max_iki_s": max(ikis) if ikis else 0.0,
        "burstiness": burstiness,
        "iki_entropy": ikisent,
        "hold_time_avg_s": safe_mean(hold_times),
        "hold_time_std_s": safe_std(hold_times),
        "n_hold_samples": len(hold_times),
        "correction_count": correction_count,
        "correction_rate": correction_rate,
        "pause_count": pause_count,
        "avg_long_pause_s": avg_long_pause,
        "skewness_iki": skewness(ikis),
    }

    # Basic normalization (z-like) for a few features (minimally)
    # Use simple transforms so downstream models get stable ranges
    features["log_n_key_downs"] = math.log1p(features["n_key_downs"])
    features["log_total_time_s"] = math.log1p(features["total_time_s"])

    return features

# ----- Heuristic mood mapping (explainable) -----
def heuristic_mood(features):
    """
    Conservative, explainable heuristic. This is NOT a clinical model.
    Returns a dict: {mood_label, score, reasons[]}
    """
    reasons = []
    score = 0.0  # positive => more 'agitated', negative => more 'calm/relaxed'
    kps = features.get("keys_per_sec", 0.0)
    burst = features.get("burstiness", 0.0)
    corr_rate = features.get("correction_rate", 0.0)
    pause_count = features.get("pause_count", 0.0)
    avg_hold = features.get("hold_time_avg_s", 0.0)

    # heuristics
    if kps > 5.0:
        score += 1.2
        reasons.append("High typing speed")
    elif kps < 1.0:
        score -= 0.8
        reasons.append("Very slow typing")

    if burst > 1.0:
        score += 0.8
        reasons.append("High burstiness (irregular rhythm)")

    if corr_rate > 0.15:
        score += 1.0
        reasons.append("High correction rate (possible frustration)")

    if pause_count >= 3:
        score -= 0.6
        reasons.append("Multiple long pauses (thinking/distracted)")

    if avg_hold > 0.2:
        # long key hold might indicate fatigue or slow typing -> calmer
        score -= 0.4
        reasons.append("Long average key hold time (slower/controlled)")

    # map continuous score to mood
    # score <= -0.5 -> relaxed / thoughtful
    # -0.5 < score < 0.8 -> neutral / focused
    # 0.8 <= score < 2.0 -> stressed / agitated
    # >=2.0 -> highly agitated / upset
    if score <= -0.5:
        mood = "relaxed"
        confidence = min(0.9, 1.0 - (score + 0.5))  # heuristic confidence
    elif score < 0.8:
        mood = "neutral/focused"
        confidence = 0.6
    elif score < 2.0:
        mood = "stressed/agitated"
        confidence = 0.7
    else:
        mood = "highly_agitated"
        confidence = 0.8

    return {"mood": mood, "score": round(score, 3), "confidence": round(confidence, 2), "reasons": reasons}

# ----- Endpoint -----
@app.post("/keystroke/analyze")
async def analyze_keystrokes(payload: KeystrokePayload):
    try:
        if not payload.events or len(payload.events) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 keystroke events")

        features = extract_features(payload.events)
        mood_est = heuristic_mood(features)

        # Package response
        response = {
            "features": features,
            "mood_estimate": mood_est,
            "meta": payload.meta or {},
            "generated_at": time.time()
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
