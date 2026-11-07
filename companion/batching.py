"""Pure adapter-side debounce; preserve all original event identities as members."""
import hashlib
import json


class Batcher:
    def __init__(self, quiet_seconds=1.0, max_wait=3.0):
        if not .2 <= quiet_seconds <= max_wait <= 10:raise ValueError("invalid debounce")
        self.quiet,self.max_wait=quiet_seconds,max_wait
        self.pending={}

    def add(self,event,now):
        # Controls/media must stay outside batching. Input scope verified by adapter first.
        if event.get("kind")!="text" or event.get("text","").startswith("/"):
            raise ValueError("not batchable")
        key=(event["account"],event["peer"])
        batch=self.pending.setdefault(key,{"first":now,"last":now,"events":[]})
        if any(e["id"]==event["id"] for e in batch["events"]):return
        if len(batch["events"])>=10 or sum(len(e["text"]) for e in batch["events"])+len(event["text"])+10>4000:
            raise ValueError("batch full; flush before admitting more")
        batch["events"].append(dict(event));batch["last"]=now

    def flush(self,now,force=False):
        ready=[]
        for key,b in list(self.pending.items()):
            if not force and now-b["last"]<self.quiet and now-b["first"]<self.max_wait:continue
            members=[e["id"] for e in b["events"]]
            out=dict(b["events"][-1])
            out["id"]="batch:"+hashlib.sha256(json.dumps(members).encode()).hexdigest()
            out["text"]="\n".join(e["text"] for e in b["events"])
            out["members"]=members
            ready.append(out);del self.pending[key]
        return ready
