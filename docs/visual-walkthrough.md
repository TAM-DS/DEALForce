# DEALForce visual walkthrough

[Back to the project README](../README.md)

These five screenshots show the research and review workflow in the working demo. All project economics are synthetic; the research roles are scripted. They illustrate the interface, not live research execution or production authorization.

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

## Make the human decision explicit

![Human review form with reviewer name, rationale, approve, request-revision and reject controls beside four outstanding diligence gaps](images/human-review.png)

The review surface asks for a name and rationale while keeping unresolved commercial, interconnection, operating and load-model evidence visible. This capture shows a **pending decision**, not a completed approval.

In this prototype, a named decision is an unauthenticated browser-local record. It does not authorize an investment. The README explains the controls needed for production use.
