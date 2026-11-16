import json
import random
import unittest
from collections import Counter
from unittest.mock import Mock

from word_order import MAX_CHIPS, split_context, suggest_word_order


class WordOrderTests(unittest.TestCase):
    def test_canvas_example_without_optional_models(self):
        words = split_context("share, AAC, clearly, students, the, helps, system, thoughts, their")
        result = suggest_word_order(words, "en")
        self.assertEqual(result["status"], "suggested")
        self.assertEqual(result["order"], [4, 1, 6, 5, 3, 0, 8, 7, 2])
        self.assertEqual(result["sentence"], "the AAC system helps students share their thoughts clearly")
        self.assertEqual(Counter(result["unjumbled"]), Counter(words))

    def test_other_help_and_let_sentences(self):
        rng = random.Random(42)
        for sentence in (
            "The teacher helps children read their books quietly",
            "The device helps users to express their needs",
            "The tools let learners share their opinions openly",
        ):
            expected = sentence.split()
            words = expected.copy()
            for _ in range(10):
                rng.shuffle(words)
                with self.subTest(words=words):
                    self.assertEqual(suggest_word_order(words, "en")["unjumbled"], expected)
            self.assertEqual(suggest_word_order(expected, "en")["status"], "unchanged")

    def test_model_keeps_repeat_occurrences_and_multiword_chips(self):
        words = ["to", "the school library", "don't", "I", "to", "want", "go"]
        generate = Mock(return_value=("```json\n[4,3,6,1,7,5,2]\n```", {}))
        result = suggest_word_order(words, "en", generate)
        self.assertEqual(result["order"], [3, 2, 5, 0, 6, 4, 1])
        self.assertEqual(result["sentence"], "I don't want to go to the school library")
        self.assertEqual(Counter(result["unjumbled"]), Counter(words))

    def test_selected_language_is_sent_to_the_model(self):
        for lang, name, words, sentence in (
            ("hi", "Hindi", ["चाहिए", "मुझे", "पानी"], "मुझे पानी चाहिए"),
            ("gu", "Gujarati", ["જોઈએ", "મને", "પાણી"], "મને પાણી જોઈએ"),
            ("mr", "Marathi", ["पाहिजे", "मला", "पाणी"], "मला पाणी पाहिजे"),
        ):
            with self.subTest(language=lang):
                generate = Mock(return_value=("[2,3,1]", {}))
                result = suggest_word_order(words, lang, generate)
                self.assertEqual(result["sentence"], sentence)
                payload = json.loads(generate.call_args.args[0][1]["content"])
                self.assertEqual(payload["language"], name)
                self.assertEqual(list(payload["chips"].values()), words)

    def test_invalid_model_outputs_preserve_the_draft(self):
        words = ["water", "need", "I"]
        for answer in ("[3,1,1]", "[3,2]", "[3,2,4]", "[3,2,true]", "[3,2,1.0]", "I need water", "[]"):
            with self.subTest(answer=answer):
                generate = Mock(return_value=(answer, {}))
                result = suggest_word_order(words, "en", generate)
                self.assertEqual(result["status"], "no_suggestion")
                self.assertEqual(result["unjumbled"], words)
                self.assertEqual(result["order"], list(range(len(words))))

    def test_english_hmm_maps_case_and_repeated_labels_back_to_original(self):
        words = ["now", "go", "Go"]
        model = Mock(word_unigrams=Counter(words + ["go"]))
        model.unjumble.return_value = (["go", "go", "now"], -3.5)
        result = suggest_word_order(words, "en", hmm_model=model)
        self.assertEqual(result["status"], "suggested")
        self.assertEqual(result["order"], [1, 2, 0])
        self.assertEqual(result["unjumbled"], ["go", "Go", "now"])
        self.assertEqual(result["score"], -3.5)

    def test_absent_model_and_length_limits(self):
        words = ["work", "they"]
        self.assertEqual(suggest_word_order(words, "en")["status"], "no_suggestion")
        self.assertEqual(suggest_word_order(words, "en", hmm_model={})["unjumbled"], words)
        generate = Mock()
        self.assertEqual(suggest_word_order(["word"] * (MAX_CHIPS + 1), "en", generate)["status"], "too_long")
        self.assertEqual(suggest_word_order(["x" * 121, "word"], "en", generate)["status"], "too_long")
        generate.assert_not_called()

    def test_blank_and_single_chip_drafts(self):
        generate = Mock()
        for words in ([], ["Help"], ["water", " "]):
            with self.subTest(words=words):
                result = suggest_word_order(words, "en", generate)
                self.assertEqual(result["status"], "no_suggestion")
                self.assertEqual(result["unjumbled"], words)
        generate.assert_not_called()

    def test_loose_context_splits_separators_and_keeps_number_commas(self):
        self.assertEqual(split_context(" 3,000, students， share\n"), ["3,000", "students", "share"])


if __name__ == "__main__":
    unittest.main()
