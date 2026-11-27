"""Loopback-only HTTP adapter. Not a multi-user or Internet deployment server."""
import json
import mimetypes
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from .service import ROOT, BoundaryError


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise BoundaryError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise BoundaryError('Non-finite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def make_server(service, port=8000):
    web = ROOT / 'dist'
    if not (web / 'index.html').exists():
        raise BoundaryError('Run npm run build before starting the server')
    for source in (ROOT / 'web').iterdir():
        if source.is_file() and (not (web / source.name).is_file() or source.read_bytes() != (web / source.name).read_bytes()):
            raise BoundaryError('Built workspace is stale. Run npm run build and restart.')
    # Only built assets are served; source, keys, runtime state and arbitrary
    # paths never become static files. Rebuild before restarting after edits.
    assets = {f'/{p.name}': p for p in web.iterdir() if p.is_file() and p.suffix in {'.html', '.mjs', '.css', '.json'}}
    assets['/'] = web / 'index.html'
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'DEALForceLocal'

        def log_message(self, *args):
            pass  # Do not log request bodies, signing information or URLs.

        def send(self, code, body, kind='application/json', extra=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def dispatch(self, post=False):
            authority = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get_all('Host') != [authority]:
                return self.send(403, {'error': 'Use the exact local 127.0.0.1 URL'})
            path = urlsplit(self.path).path
            try:
                if post:
                    if self.headers.get_all('Origin') != [f'http://{authority}'] or self.headers.get('X-DEALForce-CSRF') != token:
                        return self.send(403, {'error': 'Origin or request token rejected'})
                    if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
                        return self.send(400, {'error': 'Expected length-delimited application/json'})
                    lengths = self.headers.get_all('Content-Length') or []
                    if len(lengths) != 1 or not lengths[0].isdigit() or not 0 < int(lengths[0]) <= 32768:
                        return self.send(400, {'error': 'Invalid request length'})
                    self.connection.settimeout(5)
                    data = strict_json(self.rfile.read(int(lengths[0])))
                    methods = {'/api/scenario': service.revise, '/api/release/request': service.request,
                               '/api/release/execute': service.execute}
                    if path not in methods:
                        return self.send(404, {'error': 'No such operation'})
                    return self.send(200, methods[path](data))
                if path == '/api/state':
                    return self.send(200, service.state())
                if path.startswith('/api/release/download/'):
                    release_id = path.removeprefix('/api/release/download/')
                    doc, receipt = service.download(release_id)
                    return self.send(200, doc, 'text/markdown; charset=utf-8', {
                        'Content-Disposition': 'attachment; filename="DEALForce-released.md"',
                        'X-Artifact-SHA256': receipt['artifact_sha256'], 'X-Release-ID': receipt['release_id']})
                if path not in assets:
                    return self.send(404, {'error': 'Not found'})
                body = assets[path].read_bytes()
                if assets[path].suffix == '.html':
                    config = json.dumps({'csrf': token})
                    body = body.replace(b'</head>', f'<script>window.DEALFORCE_CONFIG={config};</script></head>'.encode())
                kind = 'text/javascript' if assets[path].suffix == '.mjs' else mimetypes.guess_type(assets[path])[0]
                return self.send(200, body, kind or 'application/octet-stream')
            except (BoundaryError, ValueError, TypeError, KeyError) as exc:
                return self.send(409, {'error': str(exc) if isinstance(exc, BoundaryError) else 'Invalid or unverifiable request/state'})
            except Exception:
                # An internal error cannot turn into an approval or a download.
                return self.send(503, {'error': 'Release unavailable. Inspect the local runtime; no release is confirmed.'})

        def do_GET(self):
            self.dispatch()

        def do_POST(self):
            self.dispatch(post=True)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
