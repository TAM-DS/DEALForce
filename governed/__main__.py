"""Local reviewer CLI. No reviewer signing operation is exposed over HTTP."""
import argparse
import hashlib
import json
from .setup import DEFAULT_HOME, DEFAULT_KEY, initialize
from .service import ReleaseService, BoundaryError


def main():
    p = argparse.ArgumentParser(description='DEALForce × Jackline: local governed brief release')
    p.add_argument('--home', default=str(DEFAULT_HOME), help='Runtime directory outside the repository')
    sub = p.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--key', default=str(DEFAULT_KEY))
    serve = sub.add_parser('serve')
    serve.add_argument('--port', type=int, default=8000)
    sub.add_parser('status')
    sub.add_parser('audit')
    show = sub.add_parser('show')
    show.add_argument('release_id')
    review = sub.add_parser('review')
    review.add_argument('release_id')
    review.add_argument('--key', default=str(DEFAULT_KEY))
    review.add_argument('--sha256', required=True, help='Exact document hash from show')
    review.add_argument('--decision', choices=['approve', 'reject'], required=True)
    review.add_argument('--reason', required=True)
    args = p.parse_args()
    try:
        if args.command == 'init':
            home, key = initialize(args.home, args.key)
            print(f'Initialized runtime: {home}\nReviewer key: {key}\nKeep this key outside the web server and repository.')
            return
        service = ReleaseService(args.home)
        if args.command == 'serve':
            from .server import make_server
            server = make_server(service, args.port)
            print(f'DEALForce local governed mode: http://127.0.0.1:{server.server_port}', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == 'show':
            doc = service.inspect(args.release_id)
            print(doc.decode())
            print('DOCUMENT SHA-256:', hashlib.sha256(doc).hexdigest())
        elif args.command == 'review':
            result = service.review(args.release_id, args.key, args.decision == 'approve', args.reason, args.sha256)
            print(json.dumps(result, indent=2))
        elif args.command == 'audit':
            from jackline.ledger import verify
            rt = service.runtime()
            ok, message, _, head = verify(rt.ledger.path, rt.key)
            print(message + '\nAnchor (store independently): ' + head)
            if not ok:
                raise BoundaryError('Audit verification failed')
        else:
            print(json.dumps(service.state(), indent=2))
    except Exception as exc:
        p.exit(1, f'{type(exc).__name__}: {exc}\n')


if __name__ == '__main__':
    main()
