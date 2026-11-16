"""Gujarati/Marathi AAC intent, polarity and native-script regression cases."""
import re
import unittest
from aac_lexicon import BOARD
from pipeline import normalize_request
from semantic import SemanticValidator
from templates import realize


class GujaratiMarathiSupport(unittest.TestCase):
    def check_case(self, language, concepts, act, negation=False):
        items=[dict(cid=cid,label=BOARD[cid][language]) for cid in concepts]
        result=realize(items,language,forced_act=act,negation=negation)
        self.assertEqual(result['status'],'ok',result)
        self.assertFalse(re.search('[A-Za-z]',result['text']))
        ctx=normalize_request(dict(entities=[x['label'] for x in items],concept_ids=concepts,
                                   language=language,act=act,act_source='user',negation=negation))
        accepted,detail=SemanticValidator().validate(ctx,{},result['text'],language)
        self.assertTrue(accepted,(language,concepts,result,detail))
        return result['text']

    def test_native_requests_preserve_objects(self):
        for lang in ('gu','mr'):
            for cid in ('WATER','MEDICINE','FOOD','TEA'):
                with self.subTest(language=lang,concept=cid):
                    text=self.check_case(lang,[cid],'REQUEST')
                    self.assertIn(BOARD[cid][lang],text)

    def test_negative_requests_preserve_refusal(self):
        for lang,negative in [('gu','નથી'),('mr','नको')]:
            for cid in ('WATER','MEDICINE','TEA'):
                with self.subTest(language=lang,concept=cid):
                    self.assertIn(negative,self.check_case(lang,[cid],'REQUEST',True))

    def test_feelings_are_not_changed_to_requests(self):
        for lang in ('gu','mr'):
            for cid in ('HAPPY','SAD','PAIN','TIRED'):
                with self.subTest(language=lang,concept=cid):self.check_case(lang,[cid],'FEELING')

    def test_feeling_and_request(self):
        for lang in ('gu','mr'):
            with self.subTest(language=lang):self.check_case(lang,['PAIN','MEDICINE'],'FEELING_REQUEST')

    def test_help_requests(self):
        for lang in ('gu','mr'):
            with self.subTest(language=lang):self.check_case(lang,['HELP'],'REQUEST')

    def test_ambiguous_selection_is_not_invented(self):
        for lang in ('gu','mr'):
            result=realize([dict(cid='MOTHER',label=BOARD['MOTHER'][lang])],lang)
            self.assertNotEqual(result['status'],'ok')

if __name__=='__main__':unittest.main()
