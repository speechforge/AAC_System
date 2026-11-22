"""Change the local administrator credentials and revoke existing admin sessions."""
from pathlib import Path
import getpass,hashlib,json,re,secrets,sqlite3
ROOT=Path(__file__).resolve().parents[1]
config_path=ROOT/'.state/config.json'
if not config_path.exists():raise SystemExit('Start the portal once to initialize credentials.')
config=json.loads(config_path.read_text())
username=input('Admin username ['+config['admin_username']+']: ').strip() or config['admin_username']
if not re.fullmatch(r'[A-Za-z0-9_.-]{3,40}',username):raise SystemExit('Use 3–40 ASCII letters, numbers, dots, dashes or underscores.')
password=getpass.getpass('New password (at least 12 characters): ')
if len(password)<12 or password!=getpass.getpass('Confirm password: '):raise SystemExit('Passwords must match and contain at least 12 characters.')
salt=secrets.token_hex(16);config.update(admin_username=username,admin_salt=salt,admin_password_hash=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex())
config_path.write_text(json.dumps(config,indent=2)+'\n');config_path.chmod(0o600)
credentials=ROOT/'.state/ADMIN_CREDENTIALS.txt';credentials.write_text('Admin URL: /admin\nUsername: '+username+'\nPassword: '+password+'\n');credentials.chmod(0o600)
if (ROOT/'.data/portal.sqlite3').exists():
 with sqlite3.connect(ROOT/'.data/portal.sqlite3') as db:db.execute("DELETE FROM sessions WHERE role='admin'")
print('Admin credentials changed. Existing admin sessions revoked. Listener sessions were preserved.')
