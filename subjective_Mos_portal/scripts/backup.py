"""Create one consistent SQLite snapshot, then derive both CSVs from that snapshot."""
from pathlib import Path
import sqlite3,datetime,csv,io,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'.data/portal.sqlite3'
if not source.exists():raise SystemExit('Start the portal first.')
target=ROOT/'.data/backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
target.mkdir(mode=0o700,parents=True,exist_ok=False)
with sqlite3.connect(source) as src,sqlite3.connect(target/'portal.sqlite3') as dst:src.backup(dst)
participants=['participant_id','name','email','age','gender','mother_tongue','organization','registered_iso','is_excluded','trials_completed']
ratings=['participant_id','clip_id','language','score','rated_iso','trial_index','listen_count','listened_seconds','is_excluded']
def save_csv(name,columns,rows):
 output=io.StringIO(newline='');writer=csv.writer(output);writer.writerow(columns)
 for row in rows:
  values=[row.get(k,'') for k in columns]
  writer.writerow(["'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for v in values])
 (target/name).write_text(output.getvalue(),encoding='utf-8')
with sqlite3.connect(target/'portal.sqlite3') as db:
 db.row_factory=sqlite3.Row
 save_csv('participants.csv',participants,[dict(r) for r in db.execute('SELECT '+','.join(participants)+' FROM participants ORDER BY registered_iso')])
 rows=[dict(r) for r in db.execute('SELECT t.participant_id,t.clip_id,t.score,t.rated_iso,t.position+1 AS trial_index,t.play_count AS listen_count,t.listened_seconds,p.is_excluded FROM trials t JOIN participants p USING(participant_id) WHERE t.score IS NOT NULL ORDER BY rated_iso')]
 for row in rows:row['language']=row['clip_id'].split('-')[0]
 save_csv('ratings.csv',ratings,rows)
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}
(target/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
for file in target.iterdir():file.chmod(0o600)
print('Saved consistent study-data backup:',target)
