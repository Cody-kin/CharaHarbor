"""No credentials, API requests or WeChat needed."""
import json
import subprocess
import sys
import time
event=dict(id="demo-"+str(time.time_ns()),account="demo-account",peer="demo-user",
           at=time.time(),kind="text",direction="incoming",group=False,text="今天有点累。")
raise SystemExit(subprocess.run([sys.executable,"-m","companion","run"],
    input=json.dumps(event).encode()).returncode)
