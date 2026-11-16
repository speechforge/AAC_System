"""Restart an isolated Redis instance to verify actual AOF/session durability."""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from personal_service import ROOT, SessionStore, Activity, redis


class RedisDurability(unittest.TestCase):
    def test_sessions_and_all_three_sections_survive_redis_restart(self):
        directory=Path(tempfile.mkdtemp(prefix='redis-durability-',dir=ROOT/'.runtime'))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        password=secrets.token_hex(16)
        binary=ROOT/'.runtime/redis/usr/bin/redis-server'
        env={**os.environ,'LD_LIBRARY_PATH':str(ROOT/'.runtime/redis/usr/lib/x86_64-linux-gnu')}
        client=redis.Redis(host='127.0.0.1',port=port,password=password,decode_responses=True,socket_timeout=1)
        log=(directory/'redis.log').open('w')
        process=None
        def start():
            process=subprocess.Popen([str(binary),'--bind','127.0.0.1','--port',str(port),
                '--requirepass',password,'--dir',str(directory),'--appendonly','yes',
                '--appendfsync','always','--save','','--daemonize','no'],env=env,stdout=log,stderr=log)
            for _ in range(40):
                try:
                    if client.ping():return process
                except redis.RedisError:time.sleep(.05)
            process.terminate();raise AssertionError('Isolated Redis did not start')
        try:
            process=start();store=SessionStore(client)
            token,session=store.create('durability-test','personal',3600)
            for lang,word,sentence in [('gu','પાણી','મને પાણી જોઈએ છે.'),('mr','पाणी','मला पाणी हवे आहे.')]:
                store.record(session,Activity(kind='word',text=word,language=lang))
                store.record(session,Activity(kind='conversation',text=sentence,language=lang))
                store.bookmark(session,sentence,lang)
            client.shutdown(save=True);process.wait(timeout=10);process=None
            process=start();restored=store.read(token)
            for lang in ('gu','mr'):
                data=store.dashboard(restored,lang)
                self.assertEqual(len(data['recent_conversations']),1)
                self.assertEqual(len(data['frequent_words']),1)
                self.assertEqual(len(data['bookmarks']),1)
        finally:
            if process:
                try:client.shutdown(save=True)
                except redis.RedisError:process.terminate()
                process.wait(timeout=10)
            client.close();log.close();shutil.rmtree(directory)

if __name__=='__main__':unittest.main()
