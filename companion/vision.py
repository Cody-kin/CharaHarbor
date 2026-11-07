"""Bounded PNG validation, without executing a decoder or trusting MIME alone."""
import base64
import struct
import zlib
from .core import Refused


def png_url(data):
    if not isinstance(data,bytes) or not 45<=len(data)<=1048576 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise Refused('vision_png_only_or_size_limit')
    at=8;compressed=[];width=height=channels=None;ended=False;chunks=0
    while at<len(data):
        if at+12>len(data):raise Refused('invalid_png')
        n=struct.unpack('>I',data[at:at+4])[0];kind=data[at+4:at+8]
        if n>1048576 or at+12+n>len(data):raise Refused('invalid_png')
        value=data[at+8:at+8+n]
        crc=struct.unpack('>I',data[at+8+n:at+12+n])[0]
        if zlib.crc32(kind+value)&0xffffffff!=crc:raise Refused('invalid_png_crc')
        if kind==b'IHDR':
            if at!=8 or n!=13:raise Refused('invalid_png')
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',value)
            if not 1<=width<=2048 or not 1<=height<=2048 or width*height>1048576 or depth!=8 or color not in (0,2,4,6) or (compression,filtering,interlace)!=(0,0,0):
                raise Refused('unsupported_png_geometry')
            channels={0:1,2:3,4:2,6:4}[color]
        elif kind==b'IDAT':compressed.append(value)
        elif kind==b'IEND':
            if n or at+12!=len(data):raise Refused('invalid_png_end')
            ended=True;break
        elif kind not in (b'sRGB',b'gAMA',b'cHRM',b'pHYs'):
            # Reject animation, text/EXIF, palettes and unknown ancillary payloads.
            raise Refused('unsupported_png_chunk')
        chunks+=1
        if chunks>128:raise Refused('too_many_png_chunks')
        at+=12+n
    if not ended or channels is None or not compressed:raise Refused('invalid_png')
    expected=height*(1+width*channels)
    decoder=zlib.decompressobj()
    raw=decoder.decompress(b''.join(compressed),expected+1)
    if len(raw)!=expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise Refused('png_decode_bounds')
    if any(raw[y*(1+width*channels)]>4 for y in range(height)):raise Refused('invalid_png_filter')
    return 'data:image/png;base64,'+base64.b64encode(data).decode('ascii')
