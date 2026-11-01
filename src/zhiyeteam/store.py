"""SQLite is the sole authoritative store; every note mutation is one transaction."""
from pathlib import Path
from datetime import datetime, timezone
import sqlite3, json, uuid, unicodedata, re
from .models import Note, ValidationError, ConflictError, MAX_BODY_BYTES, MAX_ACTIVE_NOTES

APP_ID = 0x5A595445
SCHEMA_VERSION = 1

def now(): return datetime.now(timezone.utc).isoformat(timespec="microseconds")
def ascii_lower(text): return "".join(chr(ord(c)+32) if "A"<=c<="Z" else c for c in text)
def clean_tags(values):
    if isinstance(values,str): values=re.split(r"[,，;；]",values)
    result=[]
    for value in values:
        if not isinstance(value,str): raise ValidationError("标签必须是文字")
        tag=ascii_lower(unicodedata.normalize("NFC",value.strip()))
        if not tag: continue
        if len(tag)>20: raise ValidationError("每个标签最多20个字符")
        if tag not in result: result.append(tag)
    if len(result)>20: raise ValidationError("每篇笔记最多20个标签")
    return tuple(result)

def validate_note(title,body,tags):
    title=title.strip()
    if not title or len(title)>80: raise ValidationError("标题须为1–80个字符")
    try: size=len(body.encode("utf-8",errors="strict"))
    except UnicodeError as exc: raise ValidationError("正文包含无法保存的字符") from exc
    if size>MAX_BODY_BYTES: raise ValidationError("正文不能超过1 MiB")
    return title,body,clean_tags(tags)

class NoteStore:
    def __init__(self,path):
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path,timeout=5)
        self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA trusted_schema=OFF")
        tables={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables and self.conn.execute("PRAGMA application_id").fetchone()[0]!=APP_ID:
            self.conn.close();raise ValidationError("这不是知页数据库，请选择正确的数据目录")
        if tables and self.conn.execute("PRAGMA user_version").fetchone()[0]!=SCHEMA_VERSION:
            self.conn.close();raise ValidationError("数据库版本不受支持，请先备份并检查版本")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        self.conn.execute(f"PRAGMA application_id={APP_ID}");self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.conn.commit()

    def close(self): self.conn.close()
    def _note(self,row):
        tags=tuple(r[0] for r in self.conn.execute("SELECT t.name FROM tags t JOIN note_tags nt ON nt.tag_id=t.id WHERE nt.note_id=? ORDER BY t.name",(row["id"],)))
        return Note(row["id"],row["title"],row["body"],tags,row["created_at"],row["updated_at"],row["revision"],bool(row["deleted"]))
    def get(self,note_id):
        row=self.conn.execute("SELECT * FROM notes WHERE id=?",(note_id,)).fetchone()
        if row is None: raise ValidationError("笔记不存在或已被永久删除")
        return self._note(row)
    def list_notes(self,deleted=False):
        return [self._note(r) for r in self.conn.execute("SELECT * FROM notes WHERE deleted=? ORDER BY updated_at DESC,id",(int(deleted),)).fetchall()]
    def _set_tags(self,note_id,tags):
        self.conn.execute("DELETE FROM note_tags WHERE note_id=?",(note_id,))
        for tag in tags:
            self.conn.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)",(tag,))
            self.conn.execute("INSERT INTO note_tags VALUES(?,(SELECT id FROM tags WHERE name=?))",(note_id,tag))
    def _history(self,note_id,action):
        row=self.get(note_id)
        self.conn.execute("INSERT INTO history(note_id,revision,title,body,tags_json,created_at,action) VALUES(?,?,?,?,?,?,?)",(row.id,row.revision,row.title,row.body,json.dumps(row.tags,ensure_ascii=False),now(),action))
    def _sync_links(self,note_id,body):
        from .links import sync_links
        sync_links(self.conn,note_id,body)
    def create(self,title="未命名笔记",body="",tags=()):
        title,body,tags=validate_note(title,body,tags)
        note_id=str(uuid.uuid4());stamp=now()
        with self.conn:
            count=self.conn.execute("SELECT count(*) FROM notes WHERE deleted=0").fetchone()[0]
            if count>=MAX_ACTIVE_NOTES: raise ValidationError("有效笔记已达5000篇，请先整理或导出")
            self.conn.execute("INSERT INTO notes VALUES(?,?,?,?,?,1,0)",(note_id,title,body,stamp,stamp))
            self._set_tags(note_id,tags);self._sync_links(note_id,body);self._history(note_id,"创建")
        return self.get(note_id)
    def save(self,note_id,title,body,tags=(),expected_revision=None,action="编辑"):
        title,body,tags=validate_note(title,body,tags)
        with self.conn:
            old=self.get(note_id)
            if old.deleted: raise ValidationError("请先从回收站恢复笔记")
            if expected_revision is not None and old.revision!=expected_revision:
                raise ConflictError("此笔记已在其他窗口修改。请另存当前内容或重新读取，原文未被覆盖。")
            if (title,body,tuple(sorted(tags)))==(old.title,old.body,tuple(sorted(old.tags))): return old
            self.conn.execute("UPDATE notes SET title=?,body=?,updated_at=?,revision=revision+1 WHERE id=?",(title,body,now(),note_id))
            self._set_tags(note_id,tags);self._sync_links(note_id,body);self._history(note_id,action)
        return self.get(note_id)
    def set_deleted(self,note_id,deleted):
        with self.conn:
            note=self.get(note_id)
            if note.deleted==deleted:return note
            if not deleted and self.stats()["active"]>=MAX_ACTIVE_NOTES:raise ValidationError("有效笔记已达5000篇")
            self.conn.execute("UPDATE notes SET deleted=?,updated_at=?,revision=revision+1 WHERE id=?",(int(deleted),now(),note_id))
            self._history(note_id,"移入回收站" if deleted else "从回收站恢复")
        return self.get(note_id)
    def purge(self,note_id):
        with self.conn:
            if not self.get(note_id).deleted:raise ValidationError("请先将笔记移入回收站")
            self.conn.execute("DELETE FROM notes WHERE id=?",(note_id,))
            self.conn.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM note_tags)")
    def versions(self,note_id):
        self.get(note_id)
        rows=self.conn.execute("SELECT * FROM history WHERE note_id=? ORDER BY revision DESC",(note_id,)).fetchall()
        return [dict(r)|{"tags":tuple(json.loads(r["tags_json"]))} for r in rows]
    def restore_version(self,note_id,history_id,expected_revision=None):
        row=self.conn.execute("SELECT * FROM history WHERE id=? AND note_id=?",(history_id,note_id)).fetchone()
        if not row:raise ValidationError("版本不存在")
        return self.save(note_id,row["title"],row["body"],json.loads(row["tags_json"]),expected_revision,action=f"回退至版本 {row['revision']}")
    def stats(self):
        active,trash=self.conn.execute("SELECT sum(deleted=0),sum(deleted=1) FROM notes").fetchone()
        return {"active":active or 0,"trash":trash or 0,"tags":self.conn.execute("SELECT count(DISTINCT tag_id) FROM note_tags nt JOIN notes n ON n.id=nt.note_id WHERE n.deleted=0").fetchone()[0],"versions":self.conn.execute("SELECT count(*) FROM history").fetchone()[0]}
    def settings(self,key,default=None):
        row=self.conn.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def set_setting(self,key,value):
        with self.conn:self.conn.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,json.dumps(value,ensure_ascii=False)))
