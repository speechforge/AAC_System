"""Execute only the actual account middleware/route definitions; no model initialization."""
import ast,unittest,sys
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse,RedirectResponse,JSONResponse
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'));import personal_service
class Routes(unittest.TestCase):
 def build(self,error):
  app=FastAPI();tree=ast.parse((ROOT/'backend/app.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=='account_gate')
  service=Mock();service.COOKIE=personal_service.COOKIE;service.redis=personal_service.redis;service.store.read.side_effect=error
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'gate','exec'),dict(app=app,HTTPException=HTTPException,personal_service=service,RedirectResponse=RedirectResponse,JSONResponse=JSONResponse))
  @app.get('/')
  def root():return {'public':True}
  @app.get('/api/personal/dashboard')
  def private():return {'private':True}
  return TestClient(app)
 def test_session_failure_public_private(self):
  client=self.build(HTTPException(401,'Sign in'));self.assertEqual(client.get('/').status_code,200);self.assertEqual(client.get('/api/personal/dashboard').status_code,401)
 def test_redis_failure_public_private(self):
  client=self.build(personal_service.redis.RedisError('offline'));self.assertEqual(client.get('/').status_code,200);self.assertEqual(client.get('/api/personal/dashboard').status_code,503)
if __name__=='__main__':unittest.main()
