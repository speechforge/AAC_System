"""Download the English-trained F5 model inside this checkout; retain existing IndicF5 weights."""
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('HF_HOME', str(ROOT / '.runtime/hf-home'))
from huggingface_hub import snapshot_download
snapshot_download('SWivid/F5-TTS', local_dir=ROOT / '.runtime/models/f5-english',
                  allow_patterns=['F5TTS_Base/model_1200000.safetensors', 'F5TTS_Base/vocab.txt', 'README.md'])
print('English model ready. Hindi/Gujarati/Marathi retain the existing IndicF5 checkpoint.')
