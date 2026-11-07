"""Cross-platform local installer. Never installs or logs into the WeChat bridge."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-deps',action='store_true',help='offline core only; no package downloads')
    parser.add_argument('--smoke',action='store_true',help='install and run offline demo, then exit')
    args=parser.parse_args()
    if sys.version_info<(3,9):raise SystemExit('Install Python 3.11+ from python.org (minimum 3.9).')
    root=Path(__file__).resolve().parent;os.chdir(root)
    target=root/'.venv'
    if target.is_symlink():raise SystemExit('Refusing symlinked .venv')
    python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():venv.EnvBuilder(with_pip=not args.no_deps).create(target)
    if not args.no_deps:
        subprocess.run([str(python),'-m','ensurepip','--upgrade'],check=True)
        dependencies=['tzdata==2026.6']
        if sys.version_info>=(3,11):dependencies.append('Pillow==13.0.0')
        subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check',*dependencies],check=True)
    command=[str(python),'demo.py'] if args.smoke else [str(python),'launch.py']
    return subprocess.call(command)


if __name__=='__main__':raise SystemExit(main())
