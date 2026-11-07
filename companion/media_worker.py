"""Optional current-Pillow child decoder; invoked by media.py, never downloads code."""
import sys
import warnings


def main():
    # On Windows the parent timeout and geometry limits remain; no Unix RLIMIT claim.
    if sys.platform!='win32':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(4,4))
        resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
    from PIL import Image
    Image.MAX_IMAGE_PIXELS=1048576
    warnings.simplefilter('error',Image.DecompressionBombWarning)
    with Image.open(sys.argv[1]) as source:
        if source.format not in ('JPEG','GIF') or source.width*source.height>1048576:
            raise ValueError('unsupported image')
        source.seek(0);source.load()
        # Fresh RGB buffer prevents EXIF, ICC, comments and animation metadata forwarding.
        converted=source.convert('RGB')
        try:
            clean=Image.frombytes('RGB',converted.size,converted.tobytes())
            try:clean.save(sys.argv[2],format='PNG',compress_level=6)
            finally:clean.close()
        finally:converted.close()


if __name__=='__main__':main()
