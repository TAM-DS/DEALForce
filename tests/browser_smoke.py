"""End-to-end Chromium check. Optional dependency: playwright==1.62.0."""
import hashlib
import functools
import json
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from governed.setup import initialize
from governed.service import ReleaseService, ROOT
from governed.server import make_server


def main():
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        home, key = initialize(Path(tmp)/'runtime', Path(tmp)/'signer/key')
        service = ReleaseService(home)
        server = make_server(service, 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        class QuietStatic(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        static = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietStatic,directory=str(ROOT/'dist')))
        threading.Thread(target=static.serve_forever,daemon=True).start()
        browser = p.chromium.launch(headless=True)
        errors = []
        try:
            page = browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror',lambda e:errors.append(str(e)))
            base = f'http://127.0.0.1:{server.server_port}'
            page.goto(base)
            expect(page.get_by_role('heading',name='Project Bluebonnet',exact=True)).to_be_visible()
            page.get_by_role('link',name='Governed release →').click()
            page.get_by_role('button',name='Prepare release request').click()
            expect(page.locator('.request .badge')).to_have_text('pending')
            r = service.state()['requests'][0]
            page.get_by_role('button',name='Check authority & release').click()
            expect(page.locator('.request .badge')).to_have_text('pending')
            reviewed = service.inspect(r['id'])
            service.review(r['id'],key,True,'Browser smoke: reviewed exact draft',r['artifact_sha256'])
            page.get_by_role('button',name='Refresh decision').click()
            expect(page.locator('.request .badge')).to_have_text('signed')
            page.get_by_role('button',name='Check authority & release').click()
            expect(page.locator('.request .badge')).to_have_text('released')
            with page.expect_download() as download_info:
                page.get_by_role('link',name='Download released brief').click()
            download = download_info.value
            data = Path(download.path()).read_bytes()
            assert data == reviewed and hashlib.sha256(data).hexdigest() == r['artifact_sha256']
            # Main workspace edits must invalidate the server-side release too.
            page.get_by_role('link',name='← Research workspace').click()
            page.get_by_role('button',name='What could change this conclusion?').first.click()
            page.locator('#realization').fill('35')
            page.locator('#delay').fill('12')
            page.get_by_role('button',name='Apply to brief',exact=True).click()
            expect(page.get_by_role('heading',name='Rework the thesis')).to_be_visible()
            page.get_by_role('link',name='Governed release →').click()
            expect(page.locator('.request .badge')).to_have_text('stale')
            page.get_by_role('button',name='Verify old approval is blocked').click()
            expect(page.locator('#release-message')).to_contain_text('STALE')
            assert service.state()['current']['snapshot']['assumptions']['delay'] == 12
            # A second tab cannot silently replace an updated revision.
            second=browser.new_page()
            second.goto(base+'/release.html')
            expect(second.get_by_role('button',name='Try slower build-out')).to_be_visible()
            page.locator('#capex').fill('67')
            page.get_by_role('button',name='Apply changed assumptions').click()
            expect(page.locator('#release-message')).to_have_text('Workspace updated.')
            second.get_by_role('button',name='Apply changed assumptions').click()
            expect(second.locator('#release-message')).to_contain_text('Revision conflict')
            second.close()
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile overflow'
            # Static mode needs neither Python API nor injected config.
            page.goto(f'http://127.0.0.1:{static.server_port}')
            expect(page.get_by_role('heading',name='Project Bluebonnet',exact=True)).to_be_visible()
            expect(page.get_by_role('link',name='Governed release →')).to_have_count(0)
            page.goto(f'http://127.0.0.1:{static.server_port}/release.html')
            expect(page.locator('#release-app')).to_contain_text('requires the local Python service')
            assert not errors, errors
            print('Browser smoke passed: signed release, exact download, cross-workspace invalidation, stale-tab conflict, mobile layout and static fallback.')
        finally:
            browser.close()
            server.shutdown()
            server.server_close()
            static.shutdown()
            static.server_close()


if __name__ == '__main__':
    main()
