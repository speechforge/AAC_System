import re
import numpy as np

def detect_segments(text, base_lang="hi"):
    """
    Splits text into chunks of English and Base Indic Language.
    Returns list of tuples: [("hi", "मुझे "), ("en", "school"), ("hi", " जाना है।")]
    """
    # Simple regex to find English words (A-Z, a-z)
    segments = []
    # Split by preserving English words
    parts = re.split(r'([a-zA-Z]+)', text)
    
    for part in parts:
        if not part.strip():
            continue
        if re.match(r'^[a-zA-Z]+$', part.strip()):
            segments.append(("en", part))
        else:
            segments.append((base_lang, part))
            
    # Merge consecutive segments of the same language
    merged = []
    for lang, txt in segments:
        if not merged:
            merged.append((lang, txt))
        else:
            prev_lang, prev_txt = merged[-1]
            if prev_lang == lang:
                merged[-1] = (lang, prev_txt + txt)
            else:
                merged.append((lang, txt))
                
    return merged

def stitch_audio(segments_audio, sr, crossfade_ms=50):
    """
    Stitches multiple numpy arrays with a small crossfade or concatenation.
    segments_audio: list of 1D numpy arrays
    """
    if not segments_audio:
        return np.array([], dtype=np.int16)
        
    final_audio = segments_audio[0]
    
    for audio in segments_audio[1:]:
        # Very simple concatenation with small pause for safety, 
        # actual boundary smoothing could do a linear crossfade
        # But for now, just concatenate with a tiny 10ms silence to avoid clicks
        silence = np.zeros(int(sr * 0.01), dtype=np.int16)
        final_audio = np.concatenate((final_audio, silence, audio))
        
    return final_audio

