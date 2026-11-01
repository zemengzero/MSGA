"""Online SQLite snapshots, strict input validation and protected restore."""
from pathlib import Path
from functools import lru_cache
import sqlite3,uuid
from .models import AppError,ValidationError
from .store import APP_ID,SCHEMA_VERSION,validate_note,now

def _signature(conn):
    return [(r[0],r[1]," ".join(r[2].split()).lower()) for r in conn.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL ORDER BY type,name")]
@lru_cache(maxsize=1)
def _expected():
    conn=sqlite3.connect(":memory:")
    conn.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    value=_signature(conn);conn.close();return value

def _validated_connection(path):
    path=Path(path).resolve()
    if not path.is_file() or not 0<path.stat().st_size<=256*1024*1024:raise ValidationError("请选择不超过256 MiB的知页备份数据库")
    conn=None
    try:
        conn=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
        conn.execute("PRAGMA trusted_schema=OFF");conn.execute("PRAGMA query_only=ON");conn.execute("BEGIN")
        if conn.execute("PRAGMA application_id").fetchone()[0]!=APP_ID or conn.execute("PRAGMA user_version").fetchone()[0]!=SCHEMA_VERSION:raise ValidationError("备份不是知页文件或版本不受支持")
        if _signature(conn)!=_expected():raise ValidationError("备份表结构不匹配，已拒绝恢复")
        if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok" or conn.execute("PRAGMA foreign_key_check").fetchone():raise ValidationError("备份完整性检查失败")
        for title,body in conn.execute("SELECT title,body FROM notes"):
            if not isinstance(title,str) or not isinstance(body,str):raise ValidationError("备份包含错误的数据类型")
            validate_note(title,body,())
        if conn.execute("SELECT count(*) FROM notes WHERE deleted=0").fetchone()[0]>5000:raise ValidationError("备份有效笔记超过5000篇")
        return conn
    except Exception as exc:
        if conn is not None:conn.close()
        if isinstance(exc,ValidationError):raise
        raise ValidationError("备份损坏或不是可识别的数据库，当前数据未修改") from exc

def inspect_backup(path):
    conn=_validated_connection(path)
    try:
        return {"notes":conn.execute("SELECT count(*) FROM notes WHERE deleted=0").fetchone()[0],"trash":conn.execute("SELECT count(*) FROM notes WHERE deleted=1").fetchone()[0],"versions":conn.execute("SELECT count(*) FROM history").fetchone()[0]}
    finally:conn.close()

def _copy(source,target):source.backup(target,pages=128,sleep=0.01)

def create_backup(store,target):
    target=Path(target).resolve()
    if target==store.path:raise ValidationError("不能用备份覆盖当前数据库")
    if target.exists():raise ValidationError("备份目标已存在，请换一个文件名")
    if store.conn.in_transaction:raise AppError("请等待当前保存完成")
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+".partial-"+uuid.uuid4().hex)
    dest=sqlite3.connect(temporary)
    try:
        _copy(store.conn,dest);dest.close();inspect_backup(temporary)
        if target.exists():raise ValidationError("备份目标刚刚被其他程序创建，请换名称")
        temporary.replace(target)
        return target
    finally:
        dest.close()
        if temporary.exists():temporary.unlink()

def restore_backup(store,source,protection_dir):
    source=Path(source).resolve()
    if source==store.path:raise ValidationError("请选择库外备份文件")
    validated=_validated_connection(source)
    protection_dir=Path(protection_dir).resolve();protection_dir.mkdir(parents=True,exist_ok=True)
    protection=protection_dir/("恢复前保护_"+uuid.uuid4().hex[:12]+".db")
    try:
        create_backup(store,protection)
        try:
            _copy(validated,store.conn)
            if store.conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise AppError("恢复后校验失败")
        except Exception as exc:
            old=_validated_connection(protection)
            try:_copy(old,store.conn)
            except Exception as rollback_error:
                store.writes_disabled=True
                raise AppError(f"恢复和自动回退均失败。当前库已停止写入，保护副本：{protection}") from rollback_error
            finally:old.close()
            raise AppError("恢复未完成，已经回退原库；保护副本："+str(protection)) from exc
        return protection
    finally:validated.close()
