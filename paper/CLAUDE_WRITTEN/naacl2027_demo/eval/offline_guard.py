#!/usr/bin/env python3
"""Run the REAL backend (indic-generative-aac/backend/app.py) with an in-process network guard:
every non-loopback connect() and DNS lookup raises, and each attempt is logged to results/offline_guard_attempts_<tag>.json.
This is NOT an OS-level disconnect (unprivileged network namespaces are blocked on this machine); it shows which calls try to leave the host.
Usage: PORT=8010 python offline_guard.py <tag>"""
import socket, sys, os, json, runpy, atexit, threading, time, pathlib
HERE = pathlib.Path(__file__).resolve().parent
TAG = sys.argv[1] if len(sys.argv) > 1 else "run"
ATT, LOCK = [], threading.Lock()
LOOP = {None, "localhost", "127.0.0.1", "::1", "0.0.0.0", ""}
def _dump():
    with LOCK:
        (HERE / f"results/offline_guard_attempts_{TAG}.json").write_text(json.dumps(sorted({tuple(a) for a in ATT}), ensure_ascii=False, indent=1))
_oc = socket.socket.connect
def _connect(self, addr, *a):
    host = addr[0] if isinstance(addr, tuple) else "unix"
    if isinstance(addr, tuple) and host not in LOOP and not str(host).startswith("127."):
        with LOCK: ATT.append(("connect", str(host), addr[1] if len(addr) > 1 else 0))
        _dump(); raise OSError(101, "blocked by offline_guard")
    return _oc(self, addr, *a)
socket.socket.connect = _connect
_g = socket.getaddrinfo
def _gai(host, *a, **k):
    if host not in LOOP and not str(host).startswith("127."):
        with LOCK: ATT.append(("dns", str(host), 0))
        _dump(); raise socket.gaierror(-2, "blocked by offline_guard")
    return _g(host, *a, **k)
socket.getaddrinfo = _gai
backend = HERE.parents[2] / "indic-generative-aac/backend"
os.chdir(backend); sys.path.insert(0, str(backend)); sys.argv = ["app.py"]
atexit.register(_dump)
runpy.run_path("app.py", run_name="__main__")
