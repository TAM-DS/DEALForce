# DEALForce × Jackline: governed brief release

An approved brief can become obsolete as soon as an assumption changes. This integration puts a real runtime check between a signed reviewer decision and release of the exact document. It gives Jackline a concrete application, and DEALForce a protected action with testable failure handling.

**Scope: one local document-release workflow.** Research roles remain scripted. Economics remain synthetic. No model, live research provider, email system, trading service or investment authority is connected.

[See the local demonstration: pending signature, expired approval denied, and revised brief released](visual-walkthrough.md#govern-release-with-jackline).

## Start on a Mac or Linux workstation

Requirements: Node.js 20+, Python 3.11+ and Git. Run these commands **inside your DEALForce checkout**, after pulling the merged change. Stop the static server first if port 8000 is occupied.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-governed.txt
npm test
npm run build
python -m unittest discover -s tests -p 'test_*.py' -v
python -m governed init
python -m governed serve
```

Open **http://127.0.0.1:8000** and choose **Governed release →**. Use that exact address: the server deliberately rejects other Host values. No API keys are required. Dependency installation needs network access; the release workflow itself does not.

`init` is a **one-time** operation and refuses to overwrite an existing policy or key. On later starts, activate `.venv`, build, and run `python -m governed serve`. The reviewer key is stored at `~/.config/dealforce-reviewer/reviewer.key`; runtime data at `~/.local/share/dealforce`. Neither belongs in Git. Back up the key securely. Losing it does not have an automatic bypass.

For separate workspaces, use `python -m governed --home /absolute/runtime/path init --key /separate/path/reviewer.key`, then the same `--home` before each subcommand. Supply `--key` to `review` when using a nondefault key. The server never receives this key path or reads the reviewer key.

The existing `npm start` static mode still works. It has browser-local demo review only and cannot authorize a Jackline release.

## A five-minute demonstration

1. Open the governed release workspace. The server calculates the fictional Bluebonnet base case using the same JavaScript model as the research screen.
2. Select **Prepare release request**. Jackline suspends the exact `brief.release` call pending approval. **Check authority & release** cannot bypass this pause.
3. Open a second terminal, enter the same checkout, and activate `.venv`. Copy the generated `python -m governed show RELEASE_ID` command to inspect the frozen draft. Verify its SHA-256 against the displayed request.
4. Run the displayed `review` command with that hash, `--decision approve`, and your own `--reason`. This signs the exact pending decision with a separate Ed25519 reviewer key. It approves document release only. `--decision reject` refuses it.
5. Back in the browser, select **Refresh decision**, then **Check authority & release**. Download the released Markdown. Its bytes match the reviewed hash; the download response includes `X-Artifact-SHA256` and `X-Release-ID`.
6. Select **Try slower build-out**: realization becomes 35%, delay 12 months, and the conclusion flips to **Rework the thesis**. Select **Verify old approval is blocked**. The backend rejects it. Returning sliders to their original values still creates a new revision; the old approval does not revive.
7. Prepare a fresh request and repeat review for the revised document. A failed investment screen may be released as research if the reviewer signs it; that does not authorize an investment.

Changes applied from the main research workspace also update the server revision. Concurrent tabs use an expected revision; an outdated tab must refresh instead of overwriting a newer scenario. Local **Approve brief** and **Export local draft** remain demonstration actions and cannot grant release authority.

## What each component owns

| Component | Responsibility |
| --- | --- |
| Browser | Proposes bounded scenario inputs, displays status, requests release. Holds no reviewer key. |
| DEALForce service | Recalculates metrics, renders exact document bytes, owns revisions and their hashes, rejects stale requests. |
| Jackline | Checks scoped expiring grants, default-deny policy, separate reviewer signature, approval expiry and persistent call state before invoking `brief.release`. |
| Reviewer CLI | Shows the frozen document and signs an explicit approve/reject decision for its hash with a rationale. |
| Release adapter | Records the exact artifact receipt under the same workspace lock used by scenario changes. |

Jackline is pinned to reviewed commit `855196ecc5598d9a2f644a05385f051b0e7df810`. Upgrading it requires rerunning integration tests.

Each request gets a 15-minute grant for **one tool and one call**. Approval expires five minutes after the request is created. Runtime policy also caps tool calls and elapsed run time. Unregistered operations have no HTTP route and no grant. The HTTP server binds only `127.0.0.1`, checks Host/Origin and a per-process CSRF token, rejects duplicate JSON keys and unexpected fields, and serves only built web assets.

The snapshot includes a monotonically increasing revision, project, assumptions, calculated metrics, evidence and evidence hashes, model version and implementation fingerprint. The frozen document has its own SHA-256. A code or evidence change requires a service restart and creates a new revision. Evidence hashes match the static application's authored records; they do not authenticate or archive ERCOT's external pages.

## Failure handling and recovery

| Trigger | Observed behavior |
| --- | --- |
| No signature, wrong signer, forged queue decision | No released download. |
| Assumptions change, including change-and-restore | Prior request is stale; old approval cannot release the current brief. |
| Policy or approval expires/changes | Runtime refuses release. Re-review a new revision. |
| Operator accidentally changes policy to unconditional allow | Application refuses release: approval is mandatory. |
| Concurrent change and release | A workspace lock orders the operations; only the matching revision can release. A later change disables download of the earlier request. |
| Repeated release click or process restart after success | Jackline replays the recorded result; the adapter is not invoked twice. |
| Process loss during publication | Persistent call remains `uncertain`; no automatic re-execution and no released download. |
| Edited signed state or audit chain | Verification fails closed. |

A denied, expired, or uncertain request is not replaced by repeatedly pressing **Prepare release request**. There is one stable call per revision. For routine denial/expiry, correct the issue and apply a deliberate revision before seeking fresh approval. **Do not delete checkpoints to retry an uncertain action.** Preserve the runtime and ledger for operator investigation. This narrow demo has no automated reconciliation endpoint or external delivery side effect.

To inspect the audit chain:

```bash
python -m governed audit
```

Store its full head hash independently when demonstrating truncation detection. The signed, hash-linked ledger and state are local. An operator who possesses the runtime HMAC key can rewrite them; deleting a tail requires an independent retained anchor to detect. No WORM storage or remote audit anchor is provisioned.

## Trust boundary

This is a **single-host, key-verified local demonstration**, not a multi-user production deployment. The configured public key establishes the signing identity `reviewer`; it does not establish a real-world name or organization. On a personal Mac, one OS user can access both roles. Separate files are not OS-level isolation. The host, application code, policy, runtime storage and reviewer CLI are trusted. Keep signing credentials out of agent workspaces and tool access.

Production adoption would require isolated service and reviewer identities, authenticated review UX, protected signing infrastructure, independently retained audit records, operational reconciliation, source ingestion and deployment hardening. Existing browser-local audit history is distinct from the backend Jackline ledger.

Changing assumptions cannot recall a file that someone already downloaded. The service blocks future downloads of stale requests; retained artifacts remain identified by their original revision and hash.

## Validation

```bash
npm test
npm run build
python -m unittest discover -s tests -p 'test_*.py' -v
```

Integration tests exercise real Jackline Ed25519 decisions, persisted state and the HTTP boundary. They cover exact released bytes, rejection/expiry, policy drift, forged approvals, state tampering, concurrency, stale approvals, restart replay and a crash after the side effect but before the success checkpoint.

Optional browser smoke test (also run in CI):

```bash
python -m pip install playwright==1.62.0
python -m playwright install chromium
python tests/browser_smoke.py
```

**Interview hook:** “I connected a research product to a reusable authorization runtime. Then I tested what happens when assumptions change after approval—or the process crashes during release.”
