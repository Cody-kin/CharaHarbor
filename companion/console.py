"""Use UTF-8 at CLI boundaries, including redirected Windows consoles."""
import sys


def configure():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
