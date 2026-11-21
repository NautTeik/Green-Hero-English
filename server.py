import base64, json, os, time, threading, urllib.request, urllib.error
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get('PORT', '8765'))
KEY = os.environ.get('GOOGLE_TTS_API_KEY', '')
VOICE = os.environ.get('GOOGLE_TTS_VOICE', 'en-US-Neural2-F')
cache = {}
recent = defaultdict(list)
lock = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def send(self, status, payload, mime='application/json'):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store' if mime=='application/json' else 'public, max-age=300')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send(200, (ROOT/'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/health':
            self.send(200, {'ok': True, 'cloud_configured': bool(KEY)})
        else:
            self.send(404, {'error':'Not found'})
    def do_POST(self):
        if self.path != '/api/tts':
            return self.send(404, {'error':'Not found'})
        if not KEY:
            return self.send(503, {'error':'Google Cloud TTS is not configured'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<1 or n>1024:
                return self.send(413, {'error':'Invalid request size'})
            req=json.loads(self.rfile.read(n))
            value=req.get('text','')
            if not isinstance(value,str) or not (1<=len(value)<=120) or any(ord(c)<32 for c in value):
                return self.send(400, {'error':'Invalid text'})
            # Only permit game vocabulary, preventing public arbitrary TTS use.
            # The browser sends item English names generated from these base names and modifiers.
            base = ['plastic bottle','plastic cup','plastic bag','plastic straw','bottle cap','plastic container','plastic spoon','plastic wrapper','plastic toothbrush','shampoo bottle','plastic pen casing','yogurt pot','cling film','soap dispenser','storage box','plastic ladle','plastic plate','banana peel','apple core','orange peel','dry leaves','vegetable stalk','coffee grounds','eggshell','potato peel','mango peel','melon rind','wilted flowers','tea leaves','leftover rice','onion skin','garlic skin','grass clippings','small twigs','sheet of paper','old newspaper','cardboard box','old book','used notebook','wrapping paper','flyer','cardboard','scrap paper','paper calendar','paper bag','postcard','envelope','cereal box','printer paper','magazine']
            allowed = {f'{mod} {name}'.strip() for name in base for mod in ['', 'used','crumpled','dirty','torn','small','large','old','wet','discarded']}
            if value not in allowed:
                return self.send(400, {'error':'Unknown game item'})
            ip=self.client_address[0]
            now=time.monotonic()
            with lock:
                recent[ip]=[t for t in recent[ip] if now-t<60]
                if len(recent[ip])>=30:
                    return self.send(429, {'error':'Too many requests'})
                recent[ip].append(now)
                cached=cache.get(value)
            if cached:
                return self.send(200, {'audioContent':cached})
            body=json.dumps({'input':{'text':value},'voice':{'languageCode':'en-US','name':VOICE},'audioConfig':{'audioEncoding':'MP3','speakingRate':0.9}}).encode()
            url='https://texttospeech.googleapis.com/v1/text:synthesize?key='+KEY
            request=urllib.request.Request(url, data=body, headers={'Content-Type':'application/json'}, method='POST')
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    result=json.load(response)
            except urllib.error.HTTPError as exc:
                print('Google Cloud TTS HTTP error:',exc.code,exc.read(400).decode(errors='replace'),flush=True)
                return self.send(502, {'error':'Google Cloud request failed; check API, billing and credentials'})
            audio=result.get('audioContent')
            if not audio:
                return self.send(502, {'error':'Google Cloud returned no audio'})
            with lock:
                if len(cache)<600: cache[value]=audio
            return self.send(200, {'audioContent':audio})
        except Exception as exc:
            print('TTS server error:',str(exc),flush=True)
            return self.send(500, {'error':'Server error'})

if __name__=='__main__':
    print(f'GREEN HERO web server listening on 0.0.0.0:{PORT}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
