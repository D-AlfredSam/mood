# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# import cv2
# import numpy as np
# import time
# from deepface import DeepFace
# from scipy.signal import find_peaks
# from collections import Counter
# import tempfile
# import os
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(title="Mood & Heart Rate Analyzer API")

# origins = ["*"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.post("/analyze-video/")
# async def analyze_video(file: UploadFile = File(...)):
#     # Validate input
#     if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
#         raise HTTPException(status_code=400, detail="Invalid video format")

#     # Save uploaded video temporarily
#     temp_dir = tempfile.mkdtemp()
#     temp_video_path = os.path.join(temp_dir, file.filename)
#     with open(temp_video_path, "wb") as f:
#         f.write(await file.read())

#     try:
#         # ---------- INITIALIZE ----------
#         cap = cv2.VideoCapture(temp_video_path)
#         fps = cap.get(cv2.CAP_PROP_FPS)
#         frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#         duration = frame_count / fps if fps > 0 else 0

#         face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

#         green_intensity = []
#         timestamps = []
#         emotions = []
#         bpm_values = []
#         FRAME_WINDOW = 5

#         start_time = time.time()

#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             current_time = time.time() - start_time
#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#             faces = face_cascade.detectMultiScale(gray, 1.3, 5)

#             for (x, y, w, h) in faces:
#                 roi = frame[y:y+h, x:x+w]

#                 # --- Emotion Detection ---
#                 try:
#                     analysis = DeepFace.analyze(roi, actions=['emotion'], enforce_detection=False)
#                     mood = analysis[0]['dominant_emotion']
#                     emotions.append(mood)
#                 except Exception:
#                     continue

#                 # --- Heart Rate (rPPG approximation) ---
#                 green_channel = np.mean(roi[:, :, 1])
#                 green_intensity.append(green_channel)
#                 timestamps.append(current_time)

#                 while timestamps and (timestamps[-1] - timestamps[0]) > FRAME_WINDOW:
#                     timestamps.pop(0)
#                     green_intensity.pop(0)

#                 if len(green_intensity) > 10:
#                     signal = np.array(green_intensity) - np.mean(green_intensity)
#                     peaks, _ = find_peaks(signal, distance=fps/2)
#                     if len(peaks) > 1:
#                         peak_intervals = np.diff(np.array(timestamps)[peaks])
#                         bpm = 60 / np.mean(peak_intervals)
#                         bpm_values.append(bpm)

#         cap.release()

#         # ---------- POST-PROCESS ----------
#         most_common_emotion = Counter(emotions).most_common(1)[0][0]
#         avg_bpm = float(np.mean(bpm_values))


#         result = {
#             "video_duration_sec": round(duration, 2),
#             "most_frequent_emotion": most_common_emotion,
#             "average_bpm": round(avg_bpm, 2)
#         }
#         print(result)
#         return JSONResponse(content=result)

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         # Cleanup
#         if os.path.exists(temp_video_path):
#             os.remove(temp_video_path)
#         os.rmdir(temp_dir)


from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import time
from deepface import DeepFace
from scipy.signal import find_peaks
from collections import Counter
import tempfile
import os
import subprocess
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mood & Heart Rate Analyzer API")

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

@app.get("/")
async def root():
    return {"message": "Mood & Heart Rate Analyzer API is running."}