"""Independent image provider; no secret persistence, URL downloads or retries."""
import base64
import json
import math
import os
import urllib.request
from .core import NoRedirect, Refused


def validate(c):
    settings=c.get('image_generation',{})
    if not isinstance(settings,dict):raise Refused('invalid_image_configuration')
    peers=settings.get('peers',[])
    if not isinstance(peers,list) or any(p not in c.get('picture_peers',[]) for p in peers):raise Refused('image_generation_scope_invalid')
    if not peers:return settings
    if settings.get('provider') not in ('openai','mock'):raise Refused('unsupported_image_provider')
    if c['mode']=='live' and settings['provider']=='mock':raise Refused('live_mock_images_denied')
    if not isinstance(settings.get('model'),str) or not settings['model']:raise Refused('image_model_required')
    if settings.get('quality','medium') not in ('low','medium','high','auto'):raise Refused('invalid_image_quality')
    value=settings.get('reserve_usd')
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=min(c['daily_usd'],c['project_usd']):raise Refused('invalid_image_reservation')
    return settings


class ImageProvider:
    """Extension boundary: generate(prompt) -> bounded metadata-free PNG bytes."""
    def __init__(self,settings):self.settings=settings

    def generate(self,prompt):
        if not isinstance(prompt,str) or not 1<=len(prompt)<=2000:raise Refused('invalid_image_prompt')
        if self.settings['provider']=='mock':
            import struct,zlib
            def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
            return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\x20\x90\x70'))+chunk(b'IEND',b'')
        key=os.environ.get('COMPANION_IMAGE_API_KEY')
        if not key:raise Refused('image_api_key_environment_missing')
        payload={'model':self.settings['model'],'prompt':prompt,'n':1,'size':'1024x1024','quality':self.settings.get('quality','medium'),'output_format':'png'}
        request=urllib.request.Request('https://api.openai.com/v1/images/generations',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.build_opener(NoRedirect).open(request,timeout=90) as response:raw=response.read(7_000_001)
        if len(raw)>7_000_000:raise Refused('image_provider_response_too_large')
        items=json.loads(raw).get('data')
        if not isinstance(items,list) or len(items)!=1 or not isinstance(items[0].get('b64_json'),str):raise Refused('image_provider_base64_required')
        try:data=base64.b64decode(items[0]['b64_json'],validate=True)
        except ValueError:raise Refused('invalid_generated_image') from None
        from .media import clean_png
        return clean_png(data)
