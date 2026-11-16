"""Speech errors must never produce substitute or dummy audio."""
import unittest
from threading import Lock
from unittest.mock import patch
import numpy as np
import tts

class SpeechContract(unittest.TestCase):
    def setUp(self):
        # Exercise inference independently of cached real/test WAVs; do not save mock audio.
        # Cache behavior has its own regression suite.
        for method, value in (("load", None), ("save", None)):
            cache_patch = patch.object(tts.audio_cache, method, return_value=value)
            cache_patch.start()
            self.addCleanup(cache_patch.stop)
        self.engine = tts.IndicF5Engine.__new__(tts.IndicF5Engine)
        self.engine.model = self.engine.vocoder = object()
        self.engine.english_model = object()
        self.engine.device = 'cpu'
        self.engine.init_error = None
        self.engine.last_audio_kind = 'none'
        self.engine.synthesis_lock = Lock()
        self.engine.prompts = {lang: {'audio': 'reference.wav', 'text': 'transcript'}
                               for lang in ('en', 'hi', 'gu', 'mr')}

    def test_gujarati_has_native_reference(self):
        config = self.engine.LANG_PROMPT_CONFIGS["gu"]
        self.assertEqual(config["reference_language"], "gu")
        self.assertNotEqual(config["file"], self.engine.LANG_PROMPT_CONFIGS["mr"]["file"])
        self.assertTrue(any("\u0a80" <= c <= "\u0aff" for c in config["text"]))

    def test_marathi_reference_has_published_matching_transcript(self):
        for language in ('hi', 'mr'):
            cfg = self.engine.LANG_PROMPT_CONFIGS[language]
            self.assertEqual(cfg['file'], 'MAR_F_WIKI_00001.wav')
            self.assertTrue(cfg['text'].startswith('दिगंतराव्दारे'))

    def test_short_words_get_enough_synthesis_time(self):
        self.engine.prompts['gu']['duration'] = 2.0
        self.engine.prompts['gu']['text'] = 'મને પાણી જોઈએ છે. કૃપા કરીને મારી મદદ કરો.'
        with patch.object(tts, 'infer_process', return_value=([.1,-.2,.1,-.1],24000,None)) as infer:
            audio, _ = self.engine.generate_speech('પાણી', 'gu')
            self.assertLess(infer.call_args.kwargs['speed'], 0.9)
            self.assertLessEqual(abs(audio.astype(np.int32)).max(), 31128)

    def test_only_project_languages(self):
        self.assertEqual({v['voice_id'] for v in self.engine.list_voices()}, {'en', 'hi', 'gu', 'mr'})
        for lang in ('pa', 'ta', 'kn', 'bn'):
            with self.assertRaises(ValueError): self.engine.generate_speech('hello', lang)

    def test_english_uses_english_reference(self):
        config = self.engine.LANG_PROMPT_CONFIGS['en']
        self.assertEqual(config['reference_language'], 'en')
        self.assertEqual(config['file'], 'basic_ref_en.wav')
        with patch.object(tts, 'infer_process', return_value=([0.1,-0.2],24000,None)) as infer:
            self.engine.generate_speech('I want water.', 'en')
            self.assertEqual(infer.call_args.args[2], 'I want water.')
            self.assertEqual(infer.call_args.kwargs['nfe_step'], 32)
            self.assertIs(infer.call_args.args[3], self.engine.english_model)
            self.assertEqual(self.engine.last_audio_kind, 'f5tts')

    def test_no_placeholder_when_unavailable(self):
        self.engine.model = None
        with self.assertRaises(RuntimeError): self.engine.generate_speech('पानी', 'hi')

    def test_voice_must_match_language(self):
        with self.assertRaises(ValueError): self.engine.generate_speech('पानी', 'hi', speaker_name='gu')

    def test_english_only_input_rejected(self):
        with self.assertRaises(ValueError): self.engine.generate_speech('water', 'gu')

    def test_inference_error_propagates(self):
        with patch.object(tts, 'infer_process', side_effect=RuntimeError('GPU failed')):
            with self.assertRaisesRegex(RuntimeError, 'GPU failed'):
                self.engine.generate_speech('पानी', 'hi')

    def test_invalid_audio_rejected(self):
        for audio in ([], [0, 0], [float('nan')]):
            with patch.object(tts, 'infer_process', return_value=(audio,24000,None)):
                with self.assertRaises(RuntimeError): self.engine.generate_speech('पानी','hi')

    def test_text_and_reference_sent_to_model(self):
        with patch.object(tts, 'infer_process', return_value=([0.1,-0.2],24000,None)) as infer:
            audio, sr = self.engine.generate_speech('મને પાણી જોઈએ છે.', 'gu')
            self.assertEqual(infer.call_args.args[:3], ('reference.wav','transcript','મને પાણી જોઈએ છે.'))
            self.assertEqual(infer.call_args.kwargs["nfe_step"], 64)
            self.assertEqual(infer.call_args.kwargs["speed"], 0.9)
            self.assertEqual(infer.call_args.kwargs["cfg_strength"], 1.0)
            self.assertEqual(sr, 24000)
            self.assertEqual(audio.dtype, np.int16)
            self.assertEqual(self.engine.last_audio_kind, 'indicf5')

if __name__ == '__main__': unittest.main()
