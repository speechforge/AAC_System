"""Start local AAC + persistent Redis without writing outside this checkout."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / '.runtime'
REDIS = RUNTIME / 'redis'
PID = RUNTIME / 'aac.pid'


def start_redis():
    binary = REDIS / 'usr/bin/redis-server'
    if not binary.exists():
        raise SystemExit('Run indic-generative-aac/scripts/setup_personal_storage.sh first.')
    REDIS.mkdir(parents=True, exist_ok=True)
    (REDIS / 'data').mkdir(exist_ok=True)
    connection = REDIS / 'connection.json'
    if not connection.exists():
        connection.write_text(json.dumps({'url': 'redis://:' + secrets.token_hex(32) + '@127.0.0.1:6380/0'}))
        connection.chmod(0o600)
    password = urlsplit(json.loads(connection.read_text())['url']).password
    config = REDIS / 'redis.conf'
    config.write_text(f'bind 127.0.0.1\nport 6380\nprotected-mode yes\nrequirepass {password}\n'
                      f'dir "{REDIS}/data"\nappendonly yes\nappendfsync everysec\nsave 60 1\n'
                      f'daemonize yes\nlogfile "{REDIS}/redis.log"\npidfile "{REDIS}/redis.pid"\n')
    config.chmod(0o600)
    sys.path.insert(0, str(ROOT / 'indic-generative-aac/backend'))
    import personal_service
    try:
        if personal_service.store.redis.ping():
            return
    except personal_service.redis.RedisError:
        pass
    env = {**os.environ, 'LD_LIBRARY_PATH': str(REDIS / 'usr/lib/x86_64-linux-gnu')}
    subprocess.run([str(binary), str(config)], env=env, check=True)
    for _ in range(20):
        try:
            if personal_service.store.redis.ping():
                return
        except personal_service.redis.RedisError:
            time.sleep(0.1)
    raise SystemExit('Redis did not start; inspect .runtime/redis/redis.log.')


def status():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3) as response:
            print(response.read().decode())
    except (OSError, urllib.error.URLError):
        print('AAC is not responding on port 8000; it may still be loading models.')


def stop():
    if PID.exists():
        pid = int(PID.read_text())
        try:
            cwd = Path(f'/proc/{pid}/cwd').resolve()
            command = Path(f'/proc/{pid}/cmdline').read_bytes()
            if cwd != ROOT / 'indic-generative-aac/backend' or b'app.py' not in command:
                raise SystemExit('PID no longer belongs to this project; refusing to stop it.')
            os.kill(pid, signal.SIGTERM)
        except FileNotFoundError:
            pass
        PID.unlink()
    print('AAC stopped. Redis remains running to preserve sessions and data.')


def start():
    RUNTIME.mkdir(exist_ok=True)
    start_redis()
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2):
            raise SystemExit('Port 8000 is already serving an app. Stop that app before starting another.')
    except urllib.error.URLError:
        pass
    with (RUNTIME / 'aac-server.log').open('a') as log:
        process = subprocess.Popen([sys.executable, '-u', 'app.py'],
            cwd=ROOT / 'indic-generative-aac/backend',
            env={**os.environ, 'PORT': '8000', 'PYTHONDONTWRITEBYTECODE': '1'},
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    PID.write_text(str(process.pid))
    print(f'AAC starting (PID {process.pid}). Open http://localhost:8000/ after model loading.')
    print('Log:', RUNTIME / 'aac-server.log')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    args = parser.parse_args()
    {'start': start, 'stop': stop, 'status': status}[args.action]()
