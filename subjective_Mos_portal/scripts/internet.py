"""Supervise the Cloudflare connector and update the stable Worker after tunnel restarts."""
from pathlib import Path
import argparse,json,os,re,signal,subprocess,sys,time,urllib.request,urllib.error,http.client,socket
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.state'

def worker_origin(origin):
 config=json.loads((STATE/'config.json').read_text());deployment=json.loads((ROOT/'config/deployment.json').read_text())
 target=urlsplit(deployment['public_url']);data=json.dumps({'origin':origin}).encode()
 headers={'Content-Type':'application/json','Authorization':'Bearer '+config['origin_key'],'User-Agent':'Mozilla/5.0 AAC-MOS-Connector'}
 # Try each resolved address while retaining normal certificate verification and SNI.
 # A newly provisioned Cloudflare hostname can briefly be ready on only one edge address.
 addresses=list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(target.hostname,443,type=socket.SOCK_STREAM)))
 last_error=None
 for address in addresses:
  connection=http.client.HTTPSConnection(target.hostname,timeout=25)
  connection._create_connection=lambda endpoint,timeout,source_address=None,chosen=address: socket.create_connection((chosen,endpoint[1]),timeout,source_address)
  try:
   connection.request('POST','/__portal/origin',body=data,headers=headers)
   response=connection.getresponse();response.read()
   if response.status==200:return
   last_error=RuntimeError('Front-door update returned HTTP '+str(response.status))
  except OSError as error:last_error=error
  finally:connection.close()
 raise last_error or RuntimeError('The public hostname did not resolve.')

def supervise():
 binary=STATE/'bin/cloudflared'
 if not binary.is_file():raise SystemExit('Install the official cloudflared binary at .state/bin/cloudflared first.')
 delay=5
 while True:
  started=time.time();logfile=STATE/'cloudflared.log';logfile.write_text('')
  with logfile.open('a') as log:
   process=subprocess.Popen([str(binary),'tunnel','--no-autoupdate','--protocol','http2','--edge-ip-version','4','--url','http://127.0.0.1:8011'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
  (STATE/'cloudflared.pid').write_text(str(process.pid))
  try:
   origin=None
   for _ in range(90):
    if process.poll() is not None:break
    matches=re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',logfile.read_text(errors='replace'))
    matches=[url for url in matches if url != 'https://api.trycloudflare.com']
    if matches:
     origin=matches[-1];break
    time.sleep(1)
   if not origin:raise RuntimeError('Tunnel did not provide a URL; inspect .state/cloudflared.log.')
   (STATE/'tunnel.json').write_text(json.dumps({'origin':origin,'created_iso':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},indent=2)+'\n')
   if (ROOT/'config/deployment.json').exists():
    while process.poll() is None:
     try:worker_origin(origin);print('Public front door updated. Responses remain on local disk.',flush=True);break
     except (OSError,RuntimeError) as error:
      print('Waiting to update public routing: '+type(error).__name__,flush=True);time.sleep(30)
   print('Cloudflare connector is running.',flush=True)
   process.wait()
  except Exception as exc:
   print(type(exc).__name__+': '+str(exc),flush=True)
  finally:
   if process.poll() is None:process.terminate()
  if time.time()-started>120:delay=5
  time.sleep(delay);delay=min(delay*2,60)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','status','supervise']);args=parser.parse_args();STATE.mkdir(exist_ok=True)
 pidfile=STATE/'internet.pid'
 if args.action=='supervise':supervise();return
 if args.action=='status':
  if (STATE/'tunnel.json').exists():print('Connector state is saved in .state/tunnel.json; public URL is in config/deployment.json.')
  else:print('Connector has not started.')
 elif args.action=='start':
  if pidfile.exists():
   pid=int(pidfile.read_text());proc=Path('/proc')/str(pid)
   if proc.exists() and b'internet.py' in (proc/'cmdline').read_bytes():raise SystemExit('Internet connector is already running.')
  with (STATE/'internet.log').open('a') as log:
   child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'supervise'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  pidfile.write_text(str(child.pid));print('Starting the Cloudflare connector. Local server must be running on port 8011.')
 else:
  if pidfile.exists():
   pid=int(pidfile.read_text());proc=Path('/proc')/str(pid)
   if proc.exists():
    assert (proc/'cwd').resolve()==ROOT and b'internet.py' in (proc/'cmdline').read_bytes(),'Unexpected process; refusing to stop it.'
    os.killpg(pid,signal.SIGTERM)
   pidfile.unlink()
  print('Internet connector stopped. Local data and local server remain intact.')
if __name__=='__main__':main()
