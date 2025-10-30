import librosa
from pydub import AudioSegment
import numpy as np

# --- CONFIGURATION ---
input_file = "./foai/deepcalm.mp3"
output_file = "output_song_tempo_changed.mp3"

# --- Load audio as mono ---
y, sr = librosa.load(input_file, sr=None, mono=True)

# --- Auto-detect BPM ---
tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
tempo = float(tempo)  # <-- convert to float
print(f"Detected BPM: {tempo:.2f}")

# --- Set target BPM ---
target_bpm = 80.0
tempo_factor = target_bpm / tempo
print(f"Tempo factor: {tempo_factor:.3f}")

# --- CHANGE TEMPO ---
y_changed = librosa.effects.time_stretch(y.astype(np.float32), rate=tempo_factor)

# --- Convert to 16-bit PCM ---
max_val = np.max(np.abs(y_changed))
if max_val > 0:
    y_int16 = np.int16(y_changed / max_val * 32767)
else:
    y_int16 = np.int16(y_changed * 32767)

# --- Create AudioSegment (mono) ---
audio_segment = AudioSegment(
    y_int16.tobytes(),
    frame_rate=sr,
    sample_width=2,
    channels=1
)

# --- Export MP3 ---
audio_segment.export(output_file, format="mp3", bitrate="192k")
print(f"✅ Tempo adjusted (factor: {tempo_factor:.3f}) and saved as {output_file}")
