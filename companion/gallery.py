"""Offline, no-fallback selection of user-supplied licensed ordinary images.

Not a native-sticker API. Used by Engine when an authenticated image sender is attached.
"""
import hashlib
from pathlib import Path


def select(root,entries,tags,used,now):
    root=Path(root).resolve()
    for e in entries:
        if e.get("rights_confirmed") is not True or not set(e.get("tags",[])).intersection(tags):continue
        if now-used.get(e["id"],-1e10)<86400:continue
        rel=Path(e["file"])
        if rel.is_absolute() or ".." in rel.parts:continue
        p=root/rel
        if any(parent.is_symlink() for parent in (p,*p.parents)) or not p.is_file():continue
        if p.resolve().parent != root:continue
        if p.suffix.lower() not in (".jpg",".jpeg",".png"):continue
        if not 1 <= p.stat().st_size <= 1048576:continue
        data=p.read_bytes()
        if not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")):continue
        if hashlib.sha256(data).hexdigest()!=e.get("sha256"):continue
        return p
    return None
