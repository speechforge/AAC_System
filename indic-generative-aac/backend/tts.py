import sys
import os
import io
import re
import time
import uuid
import tempfile
import torch
import numpy as np
import scipy.io.wavfile

try:
    from f5_tts.model import CFM, DiT
    from f5_tts.infer.utils_infer import (
        load_vocoder,
        get_tokenizer,
        preprocess_ref_audio_text,
        infer_process
    )
    from safetensors.torch import load_file
    F5_AVAILABLE = True
except ImportError as e:
    F5_AVAILABLE = False
    print(f"[IndicF5] F5-TTS libraries not available: {e}. Running in Mock Mode.")


class IndicF5Engine:
    """
    IndicF5-TTS Speech Synthesis Engine for AAC.
    Flow-matching diffusion acoustic model paired with Vocos 24kHz neural vocoder.
    Natively supports 11 Indian languages and English with zero-shot voice styling.
    """
    def __init__(self, checkpoint_dir=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if checkpoint_dir is None:
            candidates = [
                os.path.abspath(os.path.join(base_dir, "../../AI4Bharat-Indic-TTS/checkpoint")),
                "/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/AI4Bharat-Indic-TTS/checkpoint",
                os.path.abspath(os.path.join(base_dir, "../models/IndicF5")),
            ]
            for c in candidates:
                if os.path.exists(c):
                    checkpoint_dir = c
                    break

        self.checkpoint_dir = checkpoint_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.vocoder = None
        self.prompts = {}
        self.custom_voice_meta = {}  # voice_id -> {"label": str, "created_at": float}
        self.sample_rate = 24000

        # Locating prompt audio references
        prompt_candidates = [
            os.path.abspath(os.path.join(base_dir, "../../IndicF5/prompts")),
            os.path.abspath(os.path.join(base_dir, "../../IndicF5/f5_tts/infer/examples/basic")),
            "/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/IndicF5/prompts",
        ]
        self.prompts_dirs = [p for p in prompt_candidates if os.path.exists(p)]

        if F5_AVAILABLE:
            self.init_engine()
        else:
            print("[IndicF5] Fallback: F5-TTS disabled due to missing dependencies.")

    def init_engine(self):
        try:
            if not self.checkpoint_dir or not os.path.exists(self.checkpoint_dir):
                print(f"[IndicF5 ERROR] Checkpoint directory '{self.checkpoint_dir}' not found. Falling back to mock audio.")
                return

            vocab_path = os.path.join(self.checkpoint_dir, "vocab.txt")
            if not os.path.exists(vocab_path):
                vocab_path = os.path.join(self.checkpoint_dir, "checkpoints/vocab.txt")
            
            safetensors_path = os.path.join(self.checkpoint_dir, "model.safetensors")

            if not os.path.exists(safetensors_path):
                print(f"[IndicF5 ERROR] model.safetensors not found in '{self.checkpoint_dir}'.")
                return

            print(f"[IndicF5] Loading Vocos vocoder (24kHz) on {self.device}...")
            self.vocoder = load_vocoder(vocoder_name="vocos", is_local=False, device=self.device)

            print(f"[IndicF5] Initializing CFM DiT model from {vocab_path}...")
            vocab_char_map, vocab_size = get_tokenizer(vocab_path, "custom")
            self.model = CFM(
                transformer=DiT(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4, text_num_embeds=vocab_size, mel_dim=100),
                mel_spec_kwargs=dict(n_fft=1024, hop_length=256, win_length=1024, n_mel_channels=100, target_sample_rate=24000, mel_spec_type="vocos"),
                odeint_kwargs=dict(method="euler"),
                vocab_char_map=vocab_char_map,
            ).to(self.device)

            print(f"[IndicF5] Loading weights from {safetensors_path}...")
            state_dict = load_file(safetensors_path, device=str(self.device))
            cleaned_state_dict = {}
            for k, v in state_dict.items():
                new_k = k.replace("ema_model._orig_mod.", "").replace("ema_model.", "").replace("_orig_mod.", "")
                cleaned_state_dict[new_k] = v

            missing, unexpected = self.model.load_state_dict(cleaned_state_dict, strict=False)
            self.model.eval()
            print(f"[IndicF5] Model successfully loaded on {self.device}! (missing={len(missing)}, unexpected={len(unexpected)})")

            # Pre-cache speaker reference audio & text pairs
            self._load_reference_prompts()

        except Exception as e:
            print(f"[IndicF5 Init Error] Failed to initialize IndicF5: {e}")
            import traceback
            traceback.print_exc()
            self.model = None

    def _load_reference_prompts(self):
        """Pre-processes and caches reference prompts for zero-latency inference."""
        prompt_configs = {
            "indic_female": {
                "file": "PAN_F_HAPPY_00001.wav",
                "text": "ਭਹੰਪੀ ਵਿੱਚ ਸਮਾਰਕਾਂ ਦੇ ਭਵਨ ਨਿਰਮਾਣ ਕਲਾ ਦੇ ਵੇਰਵੇ ਗੁੰਝਲਦਾਰ ਅਤੇ ਹੈਰਾਨ ਕਰਨ ਵਾਲੇ ਹਨ, ਜੋ ਮੈਨੂੰ ਖੁਸ਼ ਕਰਦੇ  ਹਨ।"
            },
            "english_female": {
                "file": "basic_ref_en.wav",
                "text": "Some call me nature, others call me mother nature."
            }
        }

        for key, cfg in prompt_configs.items():
            wav_path = None
            # Search in known prompt dirs
            for p_dir in self.prompts_dirs:
                candidate = os.path.join(p_dir, cfg["file"])
                if os.path.exists(candidate):
                    wav_path = candidate
                    break

            if wav_path and os.path.exists(wav_path):
                try:
                    ref_audio, proc_text = preprocess_ref_audio_text(wav_path, cfg["text"])
                    self.prompts[key] = {
                        "audio": ref_audio,
                        "text": proc_text,
                        "path": wav_path
                    }
                    print(f"[IndicF5] Cached reference prompt '{key}' from {wav_path}")
                except Exception as e:
                    print(f"[IndicF5] Warning: could not pre-process prompt '{key}': {e}")

    def register_custom_voice(self, audio_bytes, ref_text, label=None, voice_id=None):
        """
        Registers a user-uploaded reference clip as a new zero-shot cloning voice.
        Implements the IndicF5 three-input contract (text / ref_audio_path / ref_text):
        https://huggingface.co/ai4bharat/IndicF5

        Returns the voice_id on success. Raises ValueError/RuntimeError on bad input.
        """
        ref_text = (ref_text or "").strip()
        if not ref_text:
            raise ValueError("A transcript of the reference audio is required for voice cloning.")
        if not audio_bytes or len(audio_bytes) < 100:
            raise ValueError("Reference audio file is empty or unreadable.")

        voice_id = voice_id or ("custom_" + uuid.uuid4().hex[:10])

        # Persist the upload to a temp wav file on disk (IndicF5 expects a file path)
        tmp_path = os.path.join(tempfile.gettempdir(), f"aac_voice_{voice_id}.wav")
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        if F5_AVAILABLE and self.model is not None and self.vocoder is not None:
            try:
                ref_audio, proc_text = preprocess_ref_audio_text(tmp_path, ref_text)
                self.prompts[voice_id] = {
                    "audio": ref_audio,
                    "text": proc_text,
                    "path": tmp_path,
                }
            except Exception as e:
                raise RuntimeError(f"Failed to process reference audio: {e}")
        else:
            # Model not loaded (mock mode) — still accept the upload so the UI flow
            # works end-to-end; synthesis will use the mock tone until the real
            # IndicF5 checkpoint + f5_tts package are installed.
            self.prompts[voice_id] = {"audio": None, "text": ref_text, "path": tmp_path}

        self.custom_voice_meta[voice_id] = {
            "label": label or "My Cloned Voice",
            "created_at": time.time(),
        }
        return voice_id

    def remove_custom_voice(self, voice_id):
        self.prompts.pop(voice_id, None)
        meta = self.custom_voice_meta.pop(voice_id, None)
        return meta is not None

    def list_voices(self):
        """Lists built-in presets plus any session-registered custom clones."""
        presets = [
            {"voice_id": "indic_female", "label": "Studio Female (Indic)", "type": "preset", "available": "indic_female" in self.prompts},
            {"voice_id": "english_female", "label": "Narrator Female (English)", "type": "preset", "available": "english_female" in self.prompts},
        ]
        custom = [
            {"voice_id": vid, "label": meta["label"], "type": "custom", "available": True}
            for vid, meta in self.custom_voice_meta.items()
        ]
        return presets + custom

    def generate_speech(self, text, lang="hi", code_mix=False, speaker_name="female"):
        """
        Synthesize speech using IndicF5.
        `speaker_name` may be a voice_id registered via register_custom_voice(),
        one of the built-in preset keys ("indic_female" / "english_female"),
        or the legacy "female" sentinel (language-based default selection).
        Returns:
            audio_array: np.ndarray in int16 format
            sample_rate: 24000
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            return np.zeros(self.sample_rate, dtype=np.int16), self.sample_rate

        if self.model is not None and self.vocoder is not None:
            try:
                # Select appropriate prompt style
                if speaker_name and speaker_name != "female" and speaker_name in self.prompts:
                    prompt = self.prompts.get(speaker_name)
                elif lang == "en" and not code_mix:
                    prompt = self.prompts.get("english_female") or self.prompts.get("indic_female")
                else:
                    prompt = self.prompts.get("indic_female") or self.prompts.get("english_female")

                if not prompt:
                    # Fallback on-the-fly prompt if caching was bypassed
                    prompt = self._load_fallback_prompt()

                ref_audio = prompt["audio"]
                ref_text = prompt["text"]

                audio, sr, _ = infer_process(
                    ref_audio,
                    ref_text,
                    cleaned_text,
                    self.model,
                    self.vocoder,
                    mel_spec_type="vocos",
                    speed=1.0,
                    nfe_step=16,
                    progress=None,
                    device=self.device,
                )

                # Normalize to 16-bit PCM format for scipy.io.wavfile / frontend
                audio_arr = np.array(audio)
                if audio_arr.dtype != np.int16:
                    max_val = np.max(np.abs(audio_arr))
                    if max_val > 0:
                        audio_arr = audio_arr / max_val
                    audio_arr = (audio_arr * 32767).astype(np.int16)

                return audio_arr, sr

            except Exception as e:
                print(f"[IndicF5 Synthesis Error] Error generating speech: {e}")
                import traceback
                traceback.print_exc()

        # Fallback tone generation (440Hz sine wave)
        print(f"[IndicF5 Fallback] Generating mock audio for text: {cleaned_text}")
        sr = self.sample_rate
        t = np.linspace(0, 1.2, int(sr * 1.2), False)
        audio = np.sin(440 * 2 * np.pi * t)
        audio = (audio * 32767).astype(np.int16)
        return audio, sr

    def _load_fallback_prompt(self):
        """Creates or loads a default fallback prompt if no audio files were located."""
        wav_path = "/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/IndicF5/prompts/PAN_F_HAPPY_00001.wav"
        text = "ਭਹੰਪੀ ਵਿੱਚ ਸਮਾਰਕਾਂ ਦੇ ਭਵਨ ਨਿਰਮਾਣ ਕਲਾ ਦੇ ਵੇਰਵੇ ਗੁੰਝਲਦਾਰ ਅਤੇ ਹੈਰਾਨ ਕਰਨ ਵਾਲੇ ਹਨ, ਜੋ ਮੈਨੂੰ ਖੁਸ਼ ਕਰਦੇ  ਹਨ।"
        if os.path.exists(wav_path):
            ref_audio, proc_text = preprocess_ref_audio_text(wav_path, text)
            return {"audio": ref_audio, "text": proc_text}
        raise FileNotFoundError(f"No prompt audio available at {wav_path}")


# Backwards compatibility alias
IndicTTSEngine = IndicF5Engine
