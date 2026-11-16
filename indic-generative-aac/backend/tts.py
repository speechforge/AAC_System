import sys
import os
import re
import json
import unicodedata
from threading import Lock
import torch
import numpy as np
import soundfile as sf
import audio_cache

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../IndicF5")))

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
    print(f"[IndicF5] F5-TTS libraries not available: {e}. Speech is unavailable.")


class IndicF5Engine:
    """
    IndicF5-TTS Speech Synthesis Engine for AAC.
    Flow-matching diffusion acoustic model paired with Vocos 24kHz neural vocoder.
    Hindi/Marathi use the Marathi reference; Gujarati uses a native Gujarati reference.
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
        self.device = "cpu" if os.getenv("AAC_DEVICE") == "cpu" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.english_model = None
        self.vocoder = None
        self.prompts = {}
        self.synthesis_lock = Lock()
        self.init_error = None
        self.sample_rate = 24000
        self.last_audio_kind = "none"

        # Locating prompt audio references
        prompt_candidates = [
            os.path.join(base_dir, "reference_audio"),
            os.path.abspath(os.path.join(base_dir, "../../IndicF5/prompts")),
            os.path.abspath(os.path.join(base_dir, "../../IndicF5/f5_tts/infer/examples/basic")),
            "/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/IndicF5/prompts",
        ]
        self.prompts_dirs = [p for p in prompt_candidates if os.path.exists(p)]

        if F5_AVAILABLE:
            self.init_engine()
        else:
            self.init_error = "IndicF5 dependencies are missing."

    def init_engine(self):
        try:
            if not self.checkpoint_dir or not os.path.exists(self.checkpoint_dir):
                raise FileNotFoundError(f"Checkpoint directory not found: {self.checkpoint_dir}")

            vocab_path = os.path.join(self.checkpoint_dir, "vocab.txt")
            if not os.path.exists(vocab_path):
                vocab_path = os.path.join(self.checkpoint_dir, "checkpoints/vocab.txt")
            
            safetensors_path = os.path.join(self.checkpoint_dir, "model.safetensors")

            if not os.path.exists(safetensors_path):
                raise FileNotFoundError(f"IndicF5 checkpoint missing: {safetensors_path}")

            print(f"[IndicF5] Loading Vocos vocoder (24kHz) on {self.device}...")
            self.vocoder = load_vocoder(vocoder_name="vocos", is_local=os.path.exists(os.path.join(base_assets := os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/vocos")), "config.yaml")), local_path=base_assets, device=self.device)

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
            acoustic, vocoder = {}, {}
            for key, value in state_dict.items():
                key = key.replace("_orig_mod.", "")
                if key.startswith("ema_model."):
                    acoustic[key[len("ema_model."):]] = value
                elif key.startswith("vocoder."):
                    vocoder[key[len("vocoder."):]] = value
                else:
                    raise RuntimeError(f"Unrecognized IndicF5 checkpoint tensor: {key}")
            self.model.load_state_dict(acoustic, strict=True)
            self.vocoder.load_state_dict(vocoder, strict=True)
            self.model.eval()
            print(f"[IndicF5] Strictly loaded {len(acoustic)} acoustic and {len(vocoder)} vocoder tensors.")
            del state_dict, acoustic, vocoder

            # IndicF5's published language list does not include English. Use the
            # original English-trained F5 model and its own vocabulary for English.
            english_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                "../../.runtime/models/f5-english/F5TTS_Base"))
            english_vocab, english_size = get_tokenizer(os.path.join(english_dir, "vocab.txt"), "custom")
            self.english_model = CFM(
                transformer=DiT(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512,
                                conv_layers=4, text_num_embeds=english_size, mel_dim=100),
                mel_spec_kwargs=dict(n_fft=1024, hop_length=256, win_length=1024,
                    n_mel_channels=100, target_sample_rate=24000, mel_spec_type="vocos"),
                odeint_kwargs=dict(method="euler"), vocab_char_map=english_vocab,
            ).to(self.device)
            english_state = load_file(os.path.join(english_dir, "model_1200000.safetensors"), device=self.device)
            cleaned = {}
            obsolete = {"initted", "step", "mel_spec.mel_stft.mel_scale.fb", "mel_spec.mel_stft.spectrogram.window"}
            for key, value in english_state.items():
                key = key.replace("_orig_mod.", "").removeprefix("ema_model.")
                if key not in obsolete:
                    cleaned[key] = value
            self.english_model.load_state_dict(cleaned, strict=True)
            self.english_model.eval()
            print(f"[F5 English] Strictly loaded {len(cleaned)} tensors with its English vocabulary.")
            del english_state, cleaned

            # Pre-cache speaker reference audio & text pairs
            self._load_reference_prompts()
            if set(self.prompts) != set(self.LANG_PROMPT_CONFIGS):
                raise RuntimeError("IndicF5 reference audio is unavailable.")

        except Exception as e:
            print(f"[IndicF5 Init Error] Failed to initialize IndicF5: {e}")
            import traceback
            traceback.print_exc()
            self.init_error = str(e)
            self.model = None

    # Every reference transcript must match its own human recording.
    # Gujarati is conditioned on native Gujarati rather than Marathi speech.
    # IndicF5 supports cross-language reference conditioning, not language IDs.
    LANG_PROMPT_CONFIGS = {
        lang: {
            "file": "MAR_F_WIKI_00001.wav",
            "text": "दिगंतराव्दारे अंतराळ कक्षेतला कचरा चिन्हित करण्यासाठी प्रयत्न केले जात आहे.",
            "label": label,
            "reference_language": "mr",
            "speed": 1.0,
            "nfe_step": 32,
        }
        for lang, label in (("hi", "हिन्दी"), ("gu", "ગુજરાતી"), ("mr", "मराठी"))
    }

    with open(os.path.join(os.path.dirname(__file__), "reference_audio", "gu_fleurs.json"), encoding="utf-8") as _ref_file:
        _gu_reference = json.load(_ref_file)
    LANG_PROMPT_CONFIGS["gu"] = {
        "file": "gu_fleurs.wav", "text": _gu_reference["text"],
        "label": "ગુજરાતી", "reference_language": "gu",
        "speed": 0.9, "nfe_step": 64, "cfg_strength": 1.0,
    }

    LANG_PROMPT_CONFIGS["en"] = {
        "file": "basic_ref_en.wav",
        "text": "Some call me nature, others call me mother nature.",
        "label": "English", "reference_language": "en", "speed": 1.0, "nfe_step": 32, "engine": "f5tts",
    }

    @property
    def ready(self):
        return (self.model is not None and self.english_model is not None and self.vocoder is not None
                and set(self.LANG_PROMPT_CONFIGS).issubset(self.prompts))

    def _load_reference_prompts(self):
        """Caches the configured reference for each project language."""
        # Collect all unique (file, text) configs to avoid re-processing the same wav
        processed_wavs = {}   # wav_path → (ref_audio, proc_text)

        all_configs = dict(self.LANG_PROMPT_CONFIGS)

        for lang_key, cfg in all_configs.items():
            wav_path = None
            fname = cfg["file"]
            subdir = cfg.get("subdir", "")  # e.g. "examples/basic" for English

            # Search prompt dirs
            for p_dir in self.prompts_dirs:
                candidates = [
                    os.path.join(p_dir, subdir, fname) if subdir else None,
                    os.path.join(p_dir, fname),
                ]
                for c in candidates:
                    if c and os.path.exists(c):
                        wav_path = c
                        break
                if wav_path:
                    break

            if not wav_path:
                print(f"[IndicF5] Warning: prompt wav '{fname}' not found for lang='{lang_key}', skipping.")
                continue

            try:
                if wav_path not in processed_wavs:
                    ref_audio, proc_text = preprocess_ref_audio_text(wav_path, cfg["text"])
                    processed_wavs[wav_path] = (ref_audio, proc_text)
                else:
                    ref_audio, proc_text = processed_wavs[wav_path]

                self.prompts[lang_key] = {
                    "audio": ref_audio,
                    "text":  proc_text,
                    "path":  wav_path,
                    "label": cfg.get("label", lang_key),
                    "duration": sf.info(ref_audio).duration,
                }
                print(f"[IndicF5] Cached prompt lang='{lang_key}' ({cfg.get('label','')}) from {os.path.basename(wav_path)}")
            except Exception as e:
                print(f"[IndicF5] Warning: could not pre-process prompt for lang='{lang_key}': {e}")

    def list_voices(self):
        return [{"voice_id": lang, "language": lang, "label": cfg["label"],
                 "type": "preset", "available": self.ready and lang in self.prompts,
                 "engine": cfg.get("engine", "indicf5"), "reference_language": cfg["reference_language"]}
                for lang, cfg in self.LANG_PROMPT_CONFIGS.items()]

    def generate_speech(self, text, lang="hi", code_mix=False, speaker_name=None, voice_reference=None):
        if lang not in self.LANG_PROMPT_CONFIGS:
            raise ValueError("Speech supports English (en), Hindi (hi), Gujarati (gu), and Marathi (mr).")
        if speaker_name not in (None, "female", lang):
            raise ValueError("The voice must match the selected language.")
        cleaned_text = unicodedata.normalize("NFC", text).strip()
        if lang == "gu":
            # Danda/ASCII sentence endings are normalized without changing words.
            cleaned_text = cleaned_text.replace("।", ".").replace("॥", ".")
            cleaned_text = re.sub(r"\s+", " ", cleaned_text)
            if cleaned_text and cleaned_text[-1] not in ".!?":
                cleaned_text += "."
        if not cleaned_text:
            raise ValueError("Speech text is empty.")

        # Reject English-only input rather than pronounce it as an Indic language.
        script = r"[A-Za-z]" if lang == "en" else (r"[\u0a80-\u0aff]" if lang == "gu" else r"[\u0900-\u097f]")
        if not re.search(script, cleaned_text) or (lang == "en" and re.search(r"[\u0900-\u0aff]", cleaned_text)):
            raise ValueError("Enter text in the selected language's native script.")
        config = dict(self.LANG_PROMPT_CONFIGS[lang])
        if voice_reference:
            config.update(_voice_owner=voice_reference['owner'],_voice_id=voice_reference['voice_id'],reference_hash=voice_reference['fingerprint'])
        cached = audio_cache.load(cleaned_text, lang, config)
        self.last_cache_hit = cached is not None
        if cached is not None:
            self.last_audio_kind = self.LANG_PROMPT_CONFIGS[lang].get("engine", "indicf5")
            return cached
        if not self.ready:
            raise RuntimeError(self.init_error or "Speech models are not ready.")
        prompt = voice_reference or self.prompts[lang]
        model = self.english_model if lang == "en" else self.model
        speed = config["speed"]
        # Estimate duration in the same units as F5 inference. Very short AAC
        # utterances need enough mel frames to form the whole word, not a clipped syllable.
        if prompt.get("duration"):
            base_seconds = prompt["duration"] * len(cleaned_text.encode("utf-8")) / max(1, len(prompt["text"].encode("utf-8")))
            minimum_seconds = max(0.8, 0.30 * len(cleaned_text.split()))
            speed = min(speed, base_seconds / minimum_seconds)
        with self.synthesis_lock, torch.inference_mode():
            self.last_audio_kind = "none"
            audio, sr, _ = infer_process(
                prompt["audio"], prompt["text"], cleaned_text,
                model, self.vocoder, mel_spec_type="vocos", speed=speed,
                cfg_strength=config.get("cfg_strength", 2.0),
                nfe_step=config["nfe_step"], progress=None, device=self.device,
            )
            audio_arr = np.asarray(audio)
            if audio_arr.size == 0 or not np.isfinite(audio_arr).all():
                raise RuntimeError("IndicF5 returned invalid audio.")
            if audio_arr.dtype == np.int16:
                audio_arr = audio_arr.astype(np.float32) / 32768.0
            else:
                audio_arr = audio_arr.astype(np.float32)
            audio_arr -= audio_arr.mean()
            rms = float(np.sqrt(np.mean(audio_arr ** 2)))
            if rms < 1e-4:
                raise RuntimeError("The speech model returned silence or insufficient audio energy.")
            # Normalize to a listening level with headroom. Do not boost arbitrary
            # low-level vocoder noise all the way to full-scale PCM.
            audio_arr *= min(3.0, 0.10 / rms)
            peak = float(np.max(np.abs(audio_arr)))
            if peak > 0.95:
                audio_arr *= 0.95 / peak
            fade = min(int(sr * 0.005), len(audio_arr) // 4)
            if fade:
                audio_arr[:fade] *= np.linspace(0, 1, fade)
                audio_arr[-fade:] *= np.linspace(1, 0, fade)
            audio_arr = (np.clip(audio_arr, -0.95, 0.95) * 32767).astype(np.int16)
            audio_cache.save(cleaned_text,lang,config,audio_arr,sr)
            self.last_cache_hit = False
            self.last_audio_kind = config.get("engine", "indicf5")
            if self.device == "cuda":
                torch.cuda.empty_cache()
            return audio_arr, sr


IndicTTSEngine = IndicF5Engine
