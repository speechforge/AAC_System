from tts import IndicTTSEngine
import scipy.io.wavfile

print("Initializing TTS...")
engine = IndicTTSEngine()
audio, sr = engine.generate_speech("मुझे पानी चाहिए।", lang="hi")
scipy.io.wavfile.write("test_hi.wav", sr, audio)
print("Saved test_hi.wav")
