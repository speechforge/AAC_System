import time,unittest
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from google.auth import jwt,crypt
from google.oauth2 import id_token
from fastapi import HTTPException
import personal_service as service

class GoogleVerificationTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
  pem=private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
  cls.signer=crypt.RSASigner.from_string(pem,key_id='test-key')
  cls.certs={'test-key':private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()}
 def token(self,**changes):
  now=int(time.time());claims=dict(iat=now+118,exp=now+3600,sub='local-test-subject',aud=service.PROJECT_ID,iss='https://securetoken.google.com/'+service.PROJECT_ID,firebase={'sign_in_provider':'google.com'})
  claims.update(changes);return jwt.encode(self.signer,claims).decode()
 def test_real_signature_and_two_minute_clock_skew(self):
  token=self.token()
  with patch('google.oauth2.id_token._fetch_certs',return_value=self.certs):
   with self.assertRaises(ValueError):id_token.verify_firebase_token(token,None,audience=service.PROJECT_ID)
   self.assertEqual(service.verify_google_token(token)['sub'],'local-test-subject')
 def test_invalid_identity_or_excessive_skew_still_rejected(self):
  for changes in [{'iat':int(time.time())+600},{'aud':'another-project'},{'iss':'https://wrong.test'},{'firebase':{'sign_in_provider':'password'}},{'exp':int(time.time())-1}]:
   with self.subTest(changes=changes),patch('google.oauth2.id_token._fetch_certs',return_value=self.certs):
    with self.assertRaises(HTTPException) as context:service.verify_google_token(self.token(**changes))
    self.assertEqual(context.exception.status_code,401)
 def test_forged_signature_rejected(self):
  token=self.token();head,payload,signature=token.split('.');signature=('A' if signature[0]!='A' else 'B')+signature[1:]
  with patch('google.oauth2.id_token._fetch_certs',return_value=self.certs),self.assertRaises(HTTPException):service.verify_google_token('.'.join([head,payload,signature]))
if __name__=='__main__':unittest.main()
