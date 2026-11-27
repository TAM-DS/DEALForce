# DEALForce visual walkthrough

[Back to the project README](../README.md)

These screenshots show the research and review workflow in the working demo, including an ERCOT source capture paired with its in-product evidence record. All project economics are synthetic; the research roles are scripted. The original screens illustrate browser-local research review. The final section shows the optional Jackline-backed local release service; neither mode claims live research execution or production deployment.

## Start with a reviewable thesis

![Research brief showing $6.83m base-case NPV, 12.3% IRR, four open diligence gaps and an awaiting-review status](images/research-workspace.png)

Bluebonnet clears the illustrative screening hurdle. Its metrics, conclusion, evidence links and unresolved diligence gaps appear together, with the human decision still pending.

## Ask what could change the conclusion

<img src="images/challenge-assumptions.png" alt="Assumption drawer with sliders for load realization, discharge price, project cost and operating delay, shown at base-case values" width="300">

The drawer exposes four assumptions and updates scenario NPV and IRR as they change. This capture shows the base-case inputs: 60% load realization, $180/MWh discharge price, $55m upfront cost and no operating delay. Applying a scenario invalidates any previous sign-off.

## Compare the consequences

![Four scenario cards comparing the base case, slower build-out, cost pressure and stronger price capture](images/scenario-comparison.png)

The slower-build-out preset explicitly changes load realization to 35% and delays operations by 12 months. NPV moves from **$6.83m to −$5.14m**, and IRR from **12.3% to 8.5%**, below the 12% screening hurdle. The cost and price scenarios expose other ways the thesis can change.

The load-to-price relationship is a hypothetical sensitivity, not an estimated causal relationship or an ERCOT forecast.

## Inspect what supports the brief

![Evidence room distinguishing two ERCOT source-context records from synthetic project inputs and model rules](images/evidence-room.png)

Source context, synthetic inputs and decision rules are labeled separately. Reviewers can inspect each record and its limitations. Record hashes bind the local authored content; they do not independently authenticate external pages.

## Follow E01 from primary source to bounded claim

### The primary-source notice

[![ERCOT notice M-F110525-04 confirming successful RTC+B implementation for the December 5, 2025 operating day](images/ercot-rtcb-primary-notice.png)](https://www.ercot.com/services/comm/mkt_notices/M-F110525-04)

**Source:** ERCOT, notice **M-F110525-04**, dated **December 5, 2025**. [Read the notice on ERCOT's website](https://www.ercot.com/services/comm/mkt_notices/M-F110525-04).

The notice confirms the completed RTC+B production transition and real-time clearing of energy and ancillary services. Its text was checked against the linked ERCOT page on **November 26, 2026**. The image is a user-supplied screenshot retained unchanged for this walkthrough; it is not an independently authenticated capture or a complete web archive. Source content belongs to ERCOT.

### How DEALForce uses it

![E01 evidence inspection showing the source-context claim, what it supports, what it does not establish, provenance, primary-source link and local record hash](images/e01-evidence-inspection.png)

The evidence panel makes the reasoning inspectable:

| Review question | What E01 provides |
| --- | --- |
| What is the claim? | RTC+B is operating, with real-time clearing of energy and ancillary services. |
| What does that support? | Market-design context for evaluating storage revenue. |
| What remains unproven? | Bluebonnet's revenues, dispatch and achievable prices. |
| Where can a reviewer check it? | The linked ERCOT notice, alongside the authored local paraphrase. |
| What does the hash bind? | The serialized local E01 JSON record, not the screenshot or external page. |

The hash visible in the evidence screenshot matches the repository's E01 record at the time this documentation was added:

```text
99e4afc60122835ee5d034f095138573d50be56aacae1a0f5b10d7e3eff1ce52
```

The demo's “original page is not archived” label refers to its runtime evidence pipeline. Adding this screenshot to repository documentation does not add source-page ingestion, cryptographic source authentication or a runtime archive. The synthetic project economics remain separate from this market-context evidence.

## Make the human decision explicit

![Human review form with reviewer name, rationale, approve, request-revision and reject controls beside four outstanding diligence gaps](images/human-review.png)

The review surface asks for a name and rationale while keeping unresolved commercial, interconnection, operating and load-model evidence visible. This capture shows a **pending decision**, not a completed approval.

In the static research workspace, a named decision is an unauthenticated browser-local record. It does not authorize an investment. The README explains the controls needed for production use.


## Govern release with Jackline

These unchanged screenshots were supplied from the working Mac demonstration on November 27, 2026. They show three distinct states of the optional local service. [Setup, architecture and failure handling](governed-release.md) describe the controls behind them.

### 1. Wait for a signed decision

![Revision 1 release request pending, with exact-document SHA-256, separate reviewer commands and a check-authority control](images/jackline-release-pending.png)

The request is **pending**. The reviewer inspects the frozen document and signs its exact hash in a separate terminal. A browser-local review does not authorize release. The screenshot contains public artifact hashes and local request identifiers, not signing keys.

### 2. Refuse an expired approval

![Jackline denies revision 1 release because the approval expired before execution](images/jackline-expired-release-denied.png)

The runtime reports **denied** with an explicit expiry reason. This was observed in the local walkthrough: the approval window elapsed before execution. It is not a manually chosen rejection or evidence of a simulated attacker.

### 3. Release the reviewed revision; mark the earlier request stale

![Revision 2 released with a download link, downside economics of minus $5.14m NPV and 8.5 percent IRR, and revision 1 marked stale](images/jackline-released-revision.png)

The slower-build-out scenario changes the conclusion to **Rework the thesis**. Revision 2 is **released**, while revision 1 is **stale**. Signing authorizes release of the research document even when its investment screen is unfavorable; it does not authorize an investment.

This capture shows an available **Verify old approval is blocked** button. It does not show the result of clicking it, nor a later change to the already released revision 2. The changed-and-restored approval and post-release staleness behaviors are covered by the integration tests and Chromium workflow described in the [release guide](governed-release.md#validation).

**Boundary:** single-host local service, synthetic economics, scripted research roles and key-verified reviewer decisions. Screenshots illustrate observed states; they are not independent security attestations. The backend ledger is distinct from browser-local audit history.
