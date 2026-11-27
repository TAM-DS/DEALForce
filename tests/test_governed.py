"""Integration tests use real Jackline signatures, disk checkpoints and HTTP."""
import hashlib
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from governed.setup import initialize
from governed.service import ReleaseService, BoundaryError, DEFAULT
from governed.server import make_server


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home, self.key = initialize(root / 'runtime', root / 'reviewer/key')
        self.s = ReleaseService(self.home)

    def request(self):
        c = self.s.state()['current']
        return self.s.request({'snapshot_id': c['snapshot_id']})['requests'][0]

    def approve(self, r):
        return self.s.review(r['id'], self.key, True, 'Reviewed evidence gaps and exact draft.', r['artifact_sha256'])

    def revise(self, **changes):
        c = self.s.state()['current']['snapshot']
        return self.s.revise({'asset': c['asset'], 'assumptions': {**c['assumptions'], **changes}, 'expected_revision': c['revision']})

    def test_signed_release_exact_bytes_and_restart_replay(self):
        r = self.request()
        self.assertEqual(r['status'], 'pending')
        before = self.s.inspect(r['id'])
        with self.assertRaises(BoundaryError):
            self.s.download(r['id'])
        self.assertEqual(self.s.execute({'release_id': r['id']})['requests'][0]['status'], 'pending')
        self.approve(r)
        self.assertEqual(self.s.execute({'release_id': r['id']})['requests'][0]['status'], 'released')
        after, receipt = self.s.download(r['id'])
        self.assertEqual(before, after)
        self.assertEqual(hashlib.sha256(after).hexdigest(), receipt['artifact_sha256'])
        self.s = ReleaseService(self.home)
        with patch.object(self.s, '_publish', side_effect=AssertionError('must not execute twice')):
            self.assertEqual(self.s.execute({'release_id': r['id']})['requests'][0]['status'], 'released')
        self.assertEqual(self.s.download(r['id'])[0], before)

    def test_change_then_restore_still_invalidates_approval(self):
        r = self.request()
        self.approve(r)
        self.revise(price=160)
        self.revise(price=180)
        with self.assertRaisesRegex(BoundaryError, 'STALE'):
            self.s.execute({'release_id': r['id']})
        with self.assertRaises(BoundaryError):
            self.s.download(r['id'])
        new = self.request()
        self.assertNotEqual(new['artifact_sha256'], r['artifact_sha256'])
        self.assertEqual(new['status'], 'pending')

    def test_stale_cannot_be_signed_and_wrong_hash_cannot_be_signed(self):
        r = self.request()
        with self.assertRaisesRegex(BoundaryError, 'hash differs'):
            self.s.review(r['id'], self.key, True, 'Reviewed', '0'*64)
        self.revise(delay=12)
        with self.assertRaisesRegex(BoundaryError, 'STALE'):
            self.approve(r)

    def test_denial_cannot_be_replaced_by_repeated_requests(self):
        r = self.request()
        self.s.review(r['id'], self.key, False, 'More revenue evidence required', r['artifact_sha256'])
        self.assertEqual(self.s.execute({'release_id': r['id']})['requests'][0]['status'], 'denied')
        self.assertEqual(self.request()['id'], r['id'])
        with self.assertRaises(BoundaryError):
            self.s.download(r['id'])

    def test_wrong_signer_and_unsigned_decisions_fail(self):
        r = self.request()
        _, wrong = initialize(Path(self.tmp.name)/'other', Path(self.tmp.name)/'other-key/key')
        with self.assertRaises(Exception):
            self.s.review(r['id'], wrong, True, 'Wrong signer', r['artifact_sha256'])
        rt = self.s.runtime()
        a = rt.approvals.get(r['approval_id'])
        a.status, a.resolved_by, a.reason = 'approved', 'reviewer', 'Forged with runtime HMAC only'
        rt.approvals._write(a)  # Attacker has envelope key, not reviewer key.
        with self.assertRaises(Exception):
            self.s.execute({'release_id': r['id']})
        with self.assertRaises(BoundaryError):
            self.s.download(r['id'])

    def test_expired_approval_and_policy_drift(self):
        r = self.request()
        self.approve(r)
        import time
        with patch('jackline.approvals.now', return_value=time.time()+301):
            self.assertEqual(self.s.execute({'release_id': r['id']})['requests'][0]['status'], 'denied')
        self.revise(price=181)
        r = self.request()
        self.approve(r)
        self.s.policy_path.write_text(self.s.policy_path.read_text().replace('timeout = "5m"', 'timeout = "6m"'))
        self.assertEqual(self.s.execute({'release_id': r['id']})['requests'][0]['status'], 'stale')

    def test_allow_policy_does_not_bypass_required_signature(self):
        self.s.policy_path.write_text(self.s.policy_path.read_text().replace('effect = "approve"', 'effect = "allow"'))
        with self.assertRaisesRegex(BoundaryError, 'must require approval'):
            self.request()
        self.assertEqual(self.s._state['published'], {})

    def test_crash_after_side_effect_stays_uncertain_after_restart(self):
        r = self.request()
        self.approve(r)
        publish = self.s._publish
        def crash(**kwargs):
            publish(**kwargs)
            raise SystemExit('Simulated process loss before Jackline success checkpoint')
        with patch.object(self.s, '_publish', side_effect=crash):
            with self.assertRaises(SystemExit):
                self.s.execute({'release_id': r['id']})
        self.s = ReleaseService(self.home)
        with patch.object(self.s, '_publish', side_effect=AssertionError('uncertain must not retry')):
            result = self.s.execute({'release_id': r['id']})
        self.assertEqual(result['requests'][0]['status'], 'uncertain')
        with self.assertRaises(BoundaryError):
            self.s.download(r['id'])
        self.assertEqual(self.request()['id'], r['id'])

    def test_concurrent_edits_and_release_are_serialized(self):
        r = self.request()
        self.approve(r)
        with ThreadPoolExecutor(2) as pool:
            jobs = [pool.submit(self.s.execute, {'release_id':r['id']}), pool.submit(self.revise, price=160)]
            for job in jobs:
                try:
                    job.result(timeout=10)
                except BoundaryError as exc:
                    self.assertIn('STALE', str(exc))
        with self.assertRaises(BoundaryError):
            self.s.download(r['id'])
        self.assertEqual(self.s.state()['requests'][0]['status'], 'stale')

    def test_optimistic_revision_and_strict_inputs(self):
        for value in [True, float('nan'), float('inf'), '180', 251]:
            with self.assertRaises(BoundaryError):
                self.revise(price=value)
        with self.assertRaises(BoundaryError):
            self.s.revise({'asset':'bluebonnet','assumptions':DEFAULT,'expected_revision':0})
        with self.assertRaises(BoundaryError):
            self.s.request({'snapshot_id':self.s.state()['current']['snapshot_id'],'approved':True})

    def test_state_tamper_fails_closed(self):
        r = self.request()
        raw = self.s.state_path.read_text().replace('Advance to diligence','APPROVED FOR TRADING')
        self.s.state_path.write_text(raw)
        with self.assertRaises(Exception):
            ReleaseService(self.home)

    def test_model_metrics_and_evidence_hashes_match_static_build(self):
        c = self.s.state()['current']['snapshot']
        self.assertAlmostEqual(c['metrics']['npv'], 6.8336028205, places=8)
        from governed.service import ROOT
        self.assertEqual(c['evidenceHashes'], json.loads((ROOT/'dist/evidence-manifest.json').read_text()))
        self.revise(realization=35, delay=12)
        self.assertFalse(self.s.state()['current']['snapshot']['metrics']['pass'])

    def test_http_has_no_signing_or_direct_publish_bypass(self):
        server = make_server(self.s, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        import re
        with urlopen(base) as response:
            html = response.read().decode()
        token = json.loads(re.search(r'window.DEALFORCE_CONFIG=(.*?);</script>', html)[1])['csrf']
        def post(path, data, origin=base, csrf=token):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            req = Request(base+path, data=raw, headers={'Origin':origin,'X-DEALForce-CSRF':csrf,'Content-Type':'application/json'})
            try:
                with urlopen(req) as response:
                    return response.status, json.load(response)
            except HTTPError as exc:
                return exc.code, json.load(exc)
        payload = {'snapshot_id':self.s.state()['current']['snapshot_id']}
        self.assertEqual(post('/api/release/request',payload,origin='https://evil.example')[0],403)
        self.assertEqual(post('/api/release/request',payload,csrf='fake')[0],403)
        self.assertEqual(post('/api/release/request',b'{"snapshot_id":1,"snapshot_id":2}')[0],409)
        self.assertEqual(post('/api/release/review',{'approved':True})[0],404)
        self.assertEqual(post('/api/release/publish',{})[0],404)
        code, data = post('/api/release/request',payload)
        self.assertEqual(code,200)
        r = data['requests'][0]
        code, data = post('/api/release/execute',{'release_id':r['id']})
        self.assertEqual(data['requests'][0]['status'],'pending')
        for path in ['/api/release/download/'+r['id'], '/policy.toml', '/../governed/service.py']:
            with self.assertRaises(HTTPError):
                urlopen(base+path)
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(base+'/api/state',headers={'Host':'evil.example'}))
        self.assertEqual(caught.exception.code,403)


if __name__ == '__main__':
    unittest.main()
