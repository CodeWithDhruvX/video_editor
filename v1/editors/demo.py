import librosa
import soundfile as sf
from deepfilternet import DeepFilterNet

# -----------------------------
# User config
# -----------------------------
INPUT_WAV = r"C:/Users/dhruv/Videos/2025/golang_interview_questions/17/2025-07-18 20-59-32.wav"
OUTPUT_WAV = r"C:/Users/dhruv/Videos/output.wav"

# -----------------------------
# Load DeepFilterNet3 (pretrained)
# -----------------------------
print("[INFO] Loading DeepFilterNet3 model...")
df = DeepFilterNet.from_pretrained("DeepFilterNet3")

# -----------------------------
# Run denoising
# -----------------------------
print(f"[INFO] Denoising {INPUT_WAV} ...")
denoised_audio = df.enhance_file(INPUT_WAV)

# -----------------------------
# Save result
# -----------------------------
# DeepFilterNet always outputs 16kHz mono audio
sf.write(OUTPUT_WAV, denoised_audio, 16000)
print(f"[DONE] Denoised file saved to {OUTPUT_WAV}")
