"""Start/stop the independent portal without touching the main AAC server."""
from pathlib import Path
import argparse,os,sys,subprocess,signal,urllib.request,json,time,socket
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.state'
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['start','stop','status']);args=p.parse_args();STATE.mkdir(mode=0o700,exist_ok=True)
 pidfile=STATE/'portal.pid'
 if args.action=='status':
  try:
   with urllib.request.urlopen('http://127.0.0.1:8011/api/health',timeout=4) as r:print(r.read().decode())
  except OSError:print('Portal is not responding on port 8011.')
 elif args.action=='start':
  try:
   with urllib.request.urlopen('http://127.0.0.1:8011/api/health',timeout=2):raise SystemExit('Port 8011 is already serving an app.')
  except OSError:pass
  with (STATE/'portal.log').open('a') as log:
   child=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8011','--no-access-log'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  pidfile.write_text(str(child.pid));print('Portal starting on http://localhost:8011/ . Admin credentials:',STATE/'ADMIN_CREDENTIALS.txt')
 else:
  if pidfile.exists():
   pid=int(pidfile.read_text());proc=Path('/proc')/str(pid)
   if proc.exists():
    assert (proc/'cwd').resolve()==ROOT and b'uvicorn' in (proc/'cmdline').read_bytes(),'Unexpected process; refusing to stop it.'
    os.kill(pid,signal.SIGTERM)
    for _ in range(50):
     try:
      with socket.create_connection(('127.0.0.1',8011),timeout=.2):pass
     except OSError:break
     time.sleep(.1)
   pidfile.unlink()
  print('Portal stopped. Saved responses remain on disk.')
if __name__=='__main__':main()
