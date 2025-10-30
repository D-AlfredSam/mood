import numpy as np
import librosa
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# ---------------- CONFIG ----------------
dat_file = "test.dat"  # your voice input
sr = 22050                    # sampling rate used when recording

# ---------------- LOAD DAT FILE ----------------
# If float32 samples
y = np.fromfile(dat_file, dtype=np.float32)

# If int16 samples, use:
# y = np.fromfile(dat_file, dtype=np.int16).astype(np.float32) / 32768

# Normalize
if np.max(np.abs(y)) > 0:
    y = y / np.max(np.abs(y))

# ---------------- FEATURE EXTRACTION ----------------
def extract_features(y, sr):
    features = []

    # MFCC
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    features.extend(np.mean(mfccs, axis=1))

    # Chroma
    stft = np.abs(librosa.stft(y))
    chroma = librosa.feature.chroma_stft(S=stft, sr=sr)
    features.extend(np.mean(chroma, axis=1))

    # Mel Spectrogram
    mel = librosa.feature.melspectrogram(y=y, sr=sr)
    features.extend(np.mean(mel, axis=1))

    return np.array(features)

X = extract_features(y, sr).reshape(1, -1)

# ---------------- NORMALIZATION ----------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # replace with pre-fitted scaler if using a real model

# ---------------- EMOTION PREDICTION ----------------
# Dummy SVM model (replace with your trained model)
# Labels: 0=neutral, 1=happy, 2=sad, 3=angry
dummy_X = np.random.rand(10, X.shape[1])
dummy_y = np.random.randint(0, 4, 10)
model = SVC(probability=True)
model.fit(dummy_X, dummy_y)

# Predict
pred = model.predict(X_scaled)[0]
probs = model.predict_proba(X_scaled)[0]

emotion_map = {0: "neutral", 1: "happy", 2: "sad", 3: "angry"}

print(f"Predicted Emotion: {emotion_map[pred]}")
print("Emotion Probabilities:")
for i, emotion in emotion_map.items():
    print(f"{emotion}: {probs[i]:.2f}")
