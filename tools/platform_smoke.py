"""Actual local OS smoke; synthetic content only. Run after install.py --smoke."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1];os.chdir(root)
python=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
subprocess.run([str(python),'-m','unittest','discover','-s','tests','-v'],check=True)
subprocess.run([str(python),'-m','companion','check','--config','examples/demo.json'],check=True)
if sys.platform=='win32':
    subprocess.run(['powershell','-NoProfile','-File','start.ps1','--no-deps','--smoke'],check=True)
else:
    subprocess.run(['sh','start.command' if sys.platform=='darwin' else 'start.sh','--no-deps','--smoke'],check=True)
# Exercise a real optional decoder on Linux/Windows, not merely a patched platform name.
if sys.version_info>=(3,11):
    subprocess.run([str(python),'-c',"import base64,io; from PIL import Image; from companion.media import normalize; data=base64.b64decode('R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='); result,first=normalize(data); assert first and result.startswith(b'\\x89PNG'); buffer=io.BytesIO(); Image.new('RGB',(2,2)).save(buffer,format='JPEG'); result,first=normalize(buffer.getvalue()); assert not first and result.startswith(b'\\x89PNG')"],check=True)
print(json.dumps({'status':'passed','platform':platform.platform(),'python':sys.version.split()[0],
    'wechat_login_tested':False,'billable_api_tested':False,'phone_tested':False}))
