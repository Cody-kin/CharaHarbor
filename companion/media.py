"""Bounded JPEG/GIF first-frame normalization; never forward source metadata."""
import os
import importlib.metadata
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib
from .core import Refused
from .vision import png_url


def geometry(data):
    if not isinstance(data,bytes) or not 10<=len(data)<=1048576:
        raise Refused('media_size_limit')
    if data.startswith((b'GIF87a',b'GIF89a')):
        w,h=struct.unpack('<HH',data[6:10]);kind='GIF'
    elif data.startswith(b'\xff\xd8'):
        kind='JPEG';at=2;w=h=0
        while at<len(data):
            if data[at]!=255:raise Refused('invalid_jpeg_segments')
            while at<len(data) and data[at]==255:at+=1
            if at>=len(data):break
            marker=data[at];at+=1
            if marker in (0xd9,0xda):break
            if marker in (0xd8,0x01) or 0xd0<=marker<=0xd7:continue
            if at+2>len(data):raise Refused('invalid_jpeg_segments')
            n=int.from_bytes(data[at:at+2],'big')
            if n<2 or at+n>len(data):raise Refused('invalid_jpeg_segments')
            if marker in (0xc0,0xc2):
                if n<8 or data[at+2]!=8:raise Refused('unsupported_jpeg')
                h,w=struct.unpack('>HH',data[at+3:at+7]);break
            if marker in (0xc1,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                raise Refused('unsupported_jpeg')
            at+=n
    else:raise Refused('unsupported_media_signature')
    if not 1<=w<=2048 or not 1<=h<=2048 or w*h>1048576:raise Refused('media_geometry_limit')
    if kind=='GIF':
        # Parse blocks without decoding: bound frames and aggregate frame geometry.
        if len(data)<13:raise Refused('invalid_gif')
        at=13+(3*(2**((data[10]&7)+1)) if data[10]&128 else 0);frames=0;pixels=0
        def blocks(at):
            while at<len(data):
                n=data[at];at+=1
                if not n:return at
                at+=n
                if at>len(data):break
            raise Refused('invalid_gif_blocks')
        while at<len(data):
            tag=data[at];at+=1
            if tag==0x3b:
                if at!=len(data) or not frames:raise Refused('invalid_gif_end')
                return kind,w,h,frames
            if tag==0x21:
                if at>=len(data):raise Refused('invalid_gif')
                at=blocks(at+1)
            elif tag==0x2c:
                if at+9>len(data):raise Refused('invalid_gif')
                x,y,fw,fh=struct.unpack('<HHHH',data[at:at+8]);packed=data[at+8];at+=9
                if not fw or not fh or x+fw>w or y+fh>h:raise Refused('invalid_gif_frame')
                frames+=1;pixels+=fw*fh
                if frames>60 or pixels>8388608:raise Refused('gif_animation_limit')
                if packed&128:at+=3*(2**((packed&7)+1))
                if at>=len(data) or not 2<=data[at]<=8:raise Refused('invalid_gif_lzw')
                at=blocks(at+1)
            else:raise Refused('invalid_gif_block')
        raise Refused('invalid_gif_end')
    return kind,w,h,1


def clean_png(data):
    """Drop decoder-emitted ancillary metadata, checking every chunk CRC first."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)>5242880:raise Refused('decoder_output_invalid')
    result=data[:8];at=8
    while at<len(data):
        if at+12>len(data):raise Refused('decoder_output_invalid')
        n=int.from_bytes(data[at:at+4],'big');end=at+n+12;kind=data[at+4:at+8]
        if end>len(data) or zlib.crc32(data[at+4:end-4])&0xffffffff!=int.from_bytes(data[end-4:end],'big'):
            raise Refused('decoder_output_invalid')
        if kind in (b'IHDR',b'IDAT',b'IEND'):result+=data[at:end]
        elif not kind[0]&32:raise Refused('decoder_output_unsupported')
        at=end
    png_url(result)
    return result


def normalize(data):
    if isinstance(data,bytes) and data.startswith(b'\x89PNG'):
        png_url(data);return data,False
    kind,w,h,frames=geometry(data)
    # The existing Mac system decoder is isolated in a timed child process.
    # No decoder is silently installed on other platforms.
    if sys.platform=='darwin' and Path('/usr/bin/sips').is_file():
        with tempfile.TemporaryDirectory(prefix='companion-media-') as directory:
            os.chmod(directory,0o700);src=Path(directory)/('input.'+kind.lower());dst=Path(directory)/'output.png'
            src.write_bytes(data);src.chmod(0o600)
            try:
                subprocess.run(['/usr/bin/sips','-s','format','png',str(src),'--out',str(dst)],
                               stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                               timeout=5,check=True,env={'PATH':'/usr/bin:/bin','HOME':directory})
                if not dst.is_file() or dst.stat().st_size>5242880:raise Refused('decoder_output_limit')
                result=clean_png(dst.read_bytes())
            except (subprocess.SubprocessError,OSError) as e:raise Refused('media_decode_failed') from e
    else:
        if sys.version_info<(3,11):raise Refused('jpeg_gif_requires_python311')
        try:version=importlib.metadata.version('Pillow')
        except importlib.metadata.PackageNotFoundError:raise Refused('jpeg_gif_decoder_unavailable') from None
        try:
            if int(version.split('.')[0])<13:raise Refused('jpeg_gif_decoder_outdated')
        except ValueError:raise Refused('jpeg_gif_decoder_version_invalid') from None
        with tempfile.TemporaryDirectory(prefix='companion-media-') as directory:
            os.chmod(directory,0o700);src=Path(directory)/'input';dst=Path(directory)/'output.png'
            src.write_bytes(data);src.chmod(0o600)
            try:
                subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('media_worker.py')),str(src),str(dst)],
                               stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                               timeout=5,check=True)
                if not dst.is_file() or dst.stat().st_size>5242880:raise Refused('decoder_output_limit')
                result=clean_png(dst.read_bytes())
            except (subprocess.SubprocessError,OSError) as e:raise Refused('media_decode_failed') from e
    rw,rh=struct.unpack('>II',result[16:24])
    if (rw,rh)!=(w,h):raise Refused('decoder_geometry_changed')
    return result,kind=='GIF'  # GIF always labelled first-frame-only, including static GIF.


def image_url(data):
    normalized,first_frame=normalize(data)
    return png_url(normalized),first_frame
