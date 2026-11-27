"""Trusted single-host release service. All state transitions share a POSIX lock.

The browser cannot supply document bytes, metrics, grants, approvals or paths.
A signed reviewer decision permits one specific frozen document revision.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import uuid
from pathlib import Path

from jackline import Policy, Runtime, issue
from jackline.grants import Grant
from jackline.runtime import RunSuspended
from jackline.storage import load_signed, locked, private_dir, save_signed
from jackline.util import digest

ROOT = Path(__file__).resolve().parents[1]
TOOL = 'brief.release'
DEFAULT = {'realization': 60, 'price': 180, 'capex': 55, 'delay': 0}
LIMITS = {'realization': (10, 100), 'price': (90, 250), 'capex': (35, 90), 'delay': (0, 24)}


class BoundaryError(ValueError):
    pass


def exact(data, fields):
    if not isinstance(data, dict) or set(data) != set(fields):
        raise BoundaryError('Unexpected or missing fields')


def identifier(value):
    if not isinstance(value, str) or len(value) != 32 or any(c not in '0123456789abcdef' for c in value):
        raise BoundaryError('Invalid release identifier')


def validate(asset, assumptions):
    if asset not in ('bluebonnet', 'mesa', 'coastal'):
        raise BoundaryError('Unknown project')
    exact(assumptions, LIMITS)
    for name, (lo, hi) in LIMITS.items():
        n = assumptions[name]
        if type(n) not in (int, float) or not math.isfinite(n) or not lo <= n <= hi:
            raise BoundaryError('Invalid assumption: ' + name)


def fingerprint():
    # Include rendering and calculation code so an old approval cannot silently
    # survive a changed model, evidence set or document implementation.
    names = ['web/model.mjs', 'web/evidence.json', 'scripts/server-model.mjs', 'governed/service.py', 'governed/server.py', 'governed/setup.py', 'requirements-governed.txt']
    return digest({n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names})


def calculate(asset, assumptions):
    validate(asset, assumptions)
    r = subprocess.run(['node', str(ROOT / 'scripts/server-model.mjs')],
                       input=json.dumps({'asset': asset, 'assumptions': assumptions}, allow_nan=False),
                       text=True, capture_output=True, timeout=10, check=True, cwd=ROOT)
    return json.loads(r.stdout)


def document(snapshot):
    m = snapshot['metrics']
    lines = [f"# DEALForce — {snapshot['projectName']}", '',
             'SYNTHETIC RESEARCH DEMO — not an investment authorization.', '',
             f"Revision: {snapshot['revision']}", f"Snapshot: {digest(snapshot)}", '',
             '## Conclusion', m['conclusion'], '',
             f"15-year NPV (10%): ${m['npv']:.6f}m", f"Unlevered pre-tax IRR: {m['irr']:.6%}" if m['irr'] is not None else 'IRR: unavailable', '',
             '## Assumptions', '```json', json.dumps(snapshot['assumptions'], indent=2), '```', '',
             'The model uses 15 annual cash flows, 93% availability, 86% round-trip efficiency and 2% annual degradation.',
             'Capex is paid now; delay shifts operating cash flows. The load-to-price sensitivity is hypothetical.',
             'Tax, debt, augmentation, congestion, curtailment and optimized dispatch are excluded.', '',
             '## Evidence and limitations']
    for e in snapshot['evidence']:
        lines += [f"### {e['id']} — {e['title']}", e['claim'], '',
                  'Supports: ' + e['supports'], 'Not established: ' + e['missing'],
                  'Source: ' + (e['url'] or 'Authored synthetic/model record'),
                  'Local record SHA-256: ' + snapshot['evidenceHashes'][e['id']], '']
    lines += ['## Outstanding diligence', '- Commercial revenue evidence', '- Interconnection and schedule',
              '- Operating costs and degradation', '- Load realization and price formation', '',
              'Approval concerns release of these exact research bytes only, not investment suitability.',
              'A separate release receipt records Jackline authorization; this document is a draft until released.',
              'Model/code fingerprint: ' + snapshot['fingerprint'], '']
    return '\n'.join(lines)


class ReleaseService:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        if self.home == ROOT or ROOT in self.home.parents:
            raise BoundaryError('Runtime storage must be outside the repository and web root')
        private_dir(self.home)
        self.policy_path = self.home / 'policy.toml'
        if not self.policy_path.exists():
            raise BoundaryError('Initialize reviewer and policy first: python -m governed init')
        self.state_path = self.home / 'release-state.json'
        self.lock_path = self.home / 'workspace.lock'
        rt = self.runtime()
        with locked(self.lock_path):
            if not self.state_path.exists():
                self._state = {'revision': 0, 'current': None, 'requests': {}, 'published': {}}
                self._revision('bluebonnet', DEFAULT, rt)
            else:
                self._load(rt)
                # Do not silently trust old state after source/model changes.
                if self._state['current']['snapshot']['fingerprint'] != fingerprint():
                    c = self._state['current']['snapshot']
                    self._revision(c['asset'], c['assumptions'], rt)

    def runtime(self):
        policy = Policy.load(self.policy_path)
        rt = Runtime(policy, home=self.home / 'jackline', approval_mode='suspend')
        rt.register(TOOL, self._publish, side_effect=True)
        return rt

    def _load(self, rt):
        self._state = load_signed(self.state_path, rt.key)

    def _save(self, rt):
        save_signed(self.state_path, self._state, rt.key)

    def _revision(self, asset, assumptions, rt):
        result = calculate(asset, assumptions)
        self._state['revision'] += 1
        s = {'revision': self._state['revision'], 'asset': asset, 'projectName': result['asset']['name'],
             'assumptions': assumptions, 'metrics': result['metrics'], 'modelVersion': result['modelVersion'],
             'evidence': result['evidence'], 'evidenceHashes': result['evidenceHashes'], 'fingerprint': fingerprint()}
        text = document(s)
        self._state['current'] = {'snapshot': s, 'snapshot_id': digest(s),
                                  'artifact_sha256': hashlib.sha256(text.encode()).hexdigest(), 'document': text}
        self._save(rt)
        rt.ledger.append('dealforce', 'brief.revised', {'revision': s['revision'], 'snapshot': digest(s)})

    def _fresh(self, request=None):
        c = self._state['current']
        if c['snapshot']['fingerprint'] != fingerprint():
            raise BoundaryError('Model or evidence changed. Restart the service to prepare a new revision.')
        if request and (request['snapshot_id'] != c['snapshot_id'] or
                        request['artifact_sha256'] != c['artifact_sha256']):
            raise BoundaryError('STALE: assumptions, evidence or document revision changed. Request a fresh approval.')
        if digest(c['snapshot']) != c['snapshot_id'] or hashlib.sha256(c['document'].encode()).hexdigest() != c['artifact_sha256']:
            raise BoundaryError('Artifact integrity failed')
        return c

    def _view(self, rt):
        c = self._state['current']
        requests = []
        for r in reversed(list(self._state['requests'].values())):
            v = {k: r.get(k) for k in ['id', 'revision', 'snapshot_id', 'artifact_sha256', 'approval_id', 'status', 'message']}
            if r['snapshot_id'] != c['snapshot_id']:
                v['status'] = 'stale'
            elif r.get('approval_id') and r['status'] == 'pending':
                a = rt.approvals.get(r['approval_id'])
                v['status'] = {'approved': 'signed', 'pending': 'pending'}.get(a.status, a.status)
                v['reviewer'] = a.resolved_by
                v['reason'] = a.reason
            requests.append(v)
        return {'current': {k: v for k, v in c.items() if k != 'document'}, 'requests': requests,
                'mode': 'jackline-local', 'reviewer': 'reviewer'}

    def state(self):
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            self._fresh()
            return self._view(rt)

    def revise(self, data):
        exact(data, ['asset', 'assumptions', 'expected_revision'])
        validate(data['asset'], data['assumptions'])
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            c = self._fresh()
            if type(data['expected_revision']) is not int or data['expected_revision'] != self._state['revision']:
                raise BoundaryError('Revision conflict. Refresh before applying changes.')
            if data['asset'] != c['snapshot']['asset'] or data['assumptions'] != c['snapshot']['assumptions']:
                self._revision(data['asset'], data['assumptions'], rt)
            return self._view(rt)

    def request(self, data):
        exact(data, ['snapshot_id'])
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            c = self._fresh()
            if data['snapshot_id'] != c['snapshot_id']:
                raise BoundaryError('Snapshot changed. Refresh before requesting release.')
            # One stable call per revision: repeated clicks cannot bypass a denial
            # or start another side effect after an uncertain outcome.
            for r in self._state['requests'].values():
                if r['snapshot_id'] == c['snapshot_id']:
                    return self._view(rt)
            rid = uuid.uuid4().hex
            grant = issue(rt.key, 'brief-' + rid, [TOOL], '15m', issued_by='dealforce-local-service', max_calls=1)
            session = rt.session('Release exact research brief', grant, task_id=grant.task_id)
            r = {'id': rid, 'revision': c['snapshot']['revision'], 'snapshot_id': c['snapshot_id'],
                 'artifact_sha256': c['artifact_sha256'], 'grant': grant.to_json(), 'run_id': session.run_id,
                 'status': 'prepared', 'approval_id': None, 'message': ''}
            self._state['requests'][rid] = r
            self._save(rt)
            self._invoke(r, session, rt)
            return self._view(rt)

    def _invoke(self, request, session, rt):
        args = {k: request[k] for k in ['snapshot_id', 'artifact_sha256']}
        args['release_id'] = request['id']
        # The application always requires a signed reviewer decision even if an
        # operator accidentally replaces the approval policy with an allow rule.
        if rt.policy.evaluate(TOOL, args).effect != 'approve':
            raise BoundaryError('Release policy must require approval')
        try:
            result = session.call(TOOL, args, call_id='release')
            request['status'] = 'released' if result.ok else result.status
            request['message'] = result.message()
        except RunSuspended as exc:
            request['approval_id'] = exc.approval_id
            request['status'] = 'pending'
            request['message'] = 'Awaiting a separately signed reviewer decision.'
        self._save(rt)

    def execute(self, data):
        exact(data, ['release_id'])
        identifier(data['release_id'])
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            r = self._state['requests'].get(data['release_id'])
            if not r:
                raise BoundaryError('Unknown release request')
            try:
                self._fresh(r)
            except BoundaryError as exc:
                rt.ledger.append(r['run_id'], 'release.blocked', {'release_id': r['id'], 'reason': str(exc)})
                raise
            session = rt.resume(r['run_id'], Grant.from_json(r['grant']))
            self._invoke(r, session, rt)
            return self._view(rt)

    def _publish(self, snapshot_id, artifact_sha256, release_id):
        # Only registered with Jackline; HTTP never invokes this function.
        # Caller holds workspace.lock across freshness checks and publication.
        self._fresh({'snapshot_id': snapshot_id, 'artifact_sha256': artifact_sha256})
        receipt = {'release_id': release_id, 'snapshot_id': snapshot_id, 'artifact_sha256': artifact_sha256}
        existing = self._state['published'].get(release_id)
        if existing and existing != receipt:
            raise BoundaryError('Release id collision')
        self._state['published'][release_id] = receipt
        self._save(self.runtime())
        return receipt

    def download(self, release_id):
        identifier(release_id)
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            r = self._state['requests'].get(release_id)
            if not r or r['status'] != 'released' or release_id not in self._state['published']:
                raise BoundaryError('No completed authorized release. Pending or uncertain outcomes are not downloadable.')
            c = self._fresh(r)
            receipt = self._state['published'][release_id]
            expected = {'release_id': release_id, 'snapshot_id': c['snapshot_id'], 'artifact_sha256': c['artifact_sha256']}
            if receipt != expected:
                raise BoundaryError('Release receipt does not match the artifact')
            return c['document'].encode(), receipt

    def review(self, release_id, key_path, approve, reason, expected_sha256):
        """Operator CLI only. The HTTP server has no signing endpoint or key path."""
        if not reason.strip() or len(reason) > 1000:
            raise BoundaryError('Provide a decision rationale of 1–1000 characters')
        key_path = Path(key_path).expanduser().resolve()
        if key_path == self.home or self.home in key_path.parents or ROOT in key_path.parents:
            raise BoundaryError('Reviewer key must be outside runtime storage and the repository')
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            r = self._state['requests'].get(release_id)
            if not r or not r.get('approval_id'):
                raise BoundaryError('Unknown approval request')
            c = self._fresh(r)
            if expected_sha256 != c['artifact_sha256']:
                raise BoundaryError('Document hash differs from the reviewed bytes')
            a = rt.approvals.get(r['approval_id'])
            if a.policy_digest != rt.policy.source_digest:
                raise BoundaryError('Policy changed. Existing approval request is stale.')
            rt.approvals.resolve(a.id, approve, 'reviewer', reason,
                                 private_key=bytes.fromhex(key_path.read_text().strip()))
            rt.ledger.append(r['run_id'], 'reviewer.decision', {'release_id': r['id'], 'approved': approve,
                                                             'snapshot_id': c['snapshot_id'], 'reason': reason})
            return self._view(rt)

    def inspect(self, release_id):
        """Reviewer reads the exact server-owned bytes before signing."""
        with locked(self.lock_path):
            rt = self.runtime()
            self._load(rt)
            r = self._state['requests'].get(release_id)
            if not r:
                raise BoundaryError('Unknown release request')
            return self._fresh(r)['document'].encode()
