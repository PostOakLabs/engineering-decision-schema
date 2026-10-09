# Episode grading rubric — mechanical, for an untrusted grader

Grade every drafted episode on the six dimensions below, each scored **0, 1, or 2** against the written anchors. Sum nothing across dimensions unless the tasking asks for a total; report the six scores individually plus any hard-fail.

**The prime directive: if you hit ambiguity on any dimension — the anchor doesn't clearly apply, the episode is missing what the check needs, you would have to guess — score that dimension 0 AND flag it with one sentence saying what was ambiguous. Never interpolate, never give benefit of the doubt, never score 1 "to be safe."** A wrongly-flagged 0 costs one re-review; a charitable 2 poisons the calibration.

Worked examples below cite the three gold episodes in this directory (`gold-01` = EP-GOLD-TRID-001, reproduced · `gold-02` = EP-GOLD-REGZ-ART220-001, retrospective · `gold-03` = EP-GOLD-EPSILON-HOEPA-001, synthetic-fixture).

---

## Hard-fail conditions (check FIRST; any one = the episode fails outright, no dimension scores)

| # | Condition | How you check it |
|---|---|---|
| HF-1 | **Schema invalid.** `python -m edi_schema.cli <file>` exits nonzero. | Run the command. Quote the exit code and the first error line. Do not grade a file you did not run. |
| HF-2 | **Fabricated citation.** A cited record, document id, hash, or regulation section that does not exist or does not say what the episode claims. | Resolve at least one load-bearing citation per episode. A citation you cannot resolve is a FLAG (grade the rest, note it); a citation you resolve and find contradicted is HF-2. |
| HF-3 | **Provenance mislabel.** The `provenance` value contradicts the episode's own content — e.g. `reproduced` with no environment/recompute trail, `retrospective` citing no record, `synthetic-fixture` claiming production measurements, or (in either direction) constructed numbers presented as measured ones. | Compare the label against what the rationale and metrics actually claim. gold-03's rationale sentence "the vectors here are constructed for calibration and were not executed against any live kernel" is exactly the disclosure that keeps a synthetic episode honest; its absence plus a measurement claim = HF-3. |

⚠ Known trap (do not reproduce it): the self-serve questionnaire page emits `x_capture` and `design.scale_bucket` fields, which the closed schema REJECTS. An episode carrying them fails HF-1 mechanically. The schema is the authority; do not "fix" such an episode by mentally deleting the fields — run the validator and record what it says.

---

## Dimension 1 — Schema validity (binary in effect)

- **2** — `python -m edi_schema.cli <file>` prints `ok` and exits 0. (All three gold files; quote the run.)
- **1** — never awarded. There is no partially-valid.
- **0** — anything else (this duplicates HF-1; score 0 here and stop).

## Dimension 2 — Candidate quality

Check: `candidates_considered` has ≥2 entries beyond trivial; the rejected ones are mutually exclusive live options; every `rejected_because` names a **concrete cost** (a number, a named wrong verdict, a named rework) — not vibes.

- **2** — gold-01: the sum-of-increases candidate is rejected with the exact false figure it produces on the stated table ("$25 violation ... on a bucket whose aggregate DECREASED $30") and the class evidence (31 divergent adjudicated cases). Both rejected candidates could genuinely have been chosen by a naive implementer; they exclude each other and the winner.
- **1** — candidates are real and ≥2, but at least one `rejected_because` is generic ("less accurate", "not best practice", "could cause issues") with no number, verdict, or named cost — the shape of gold-02's rejections WITHOUT the "$341 / $10 / $68 / $3" divergences and the "gate stayed green while every tier was wrong" specifics.
- **0** — fewer than 2 rejected-or-chosen alternatives with substance; straw men (candidates nobody would pick, e.g. "do nothing" padded to reach the count); or a `rejected_because` that merely restates the choice ("rejected because the other option was better"). Also 0 if the exactly-one-null rule holds only syntactically but the null candidate's text doesn't match `chosen_intervention`.

## Dimension 3 — Measurement verifiability

Check: the numbers in `observation` and `post_state.metrics` are **recomputable from inputs stated inside the episode**. You MUST actually recompute at least the observation figure and one post_state figure, and show your arithmetic in the grading note.

- **2** — gold-01: prior_state carries every fee line; you recompute Σle=100+500+150=750, Σcd=200+400+120=720, allowed=750×1.10=825, 720≤825 → violation $0, and the rejected method's 100−75=$25 — all four match the episode. gold-03: each vector row recomputes from the two comparator strings alone (2.000 > 1.99999 true; 2.000 > 2.005 false).
- **1** — the figures are consistent and sourced, but at least one requires information outside the episode to recompute (gold-02's official tier values are retrievable only via the cited record/FR document — acceptable for retrospective, which is why gold-02 pins the record's sha256; score 1 when the citation resolves, 0 when it doesn't).
- **0** — any stated figure you recompute and get a different number; any figure with no stated inputs at all; or metrics present as 0 that were plainly never measured (the schema's own "absent, never 0" rule).

## Dimension 4 — Provenance honesty

Check: the label matches the evidentiary basis (see HF-3 for outright fails; this dimension grades degree).

- **2** — gold-02: `retrospective` AND the rationale names its records with a content hash and says what each contains ("its comparison table records kernel 134500 vs official $134,841 as DIVERGES"). gold-01: `reproduced` AND the environment block honestly declares the non-silicon mapping and the recompute performed, and design pins the source record by sha256.
- **1** — label plausibly correct but the trail is thin: retrospective citing "internal records" without naming one; reproduced whose environment strings are placeholders with no statement of what was actually re-run.
- **0** — no evidentiary trail at all, or trail contradicts the label short of an outright HF-3 (e.g. reproduced whose "recompute" is a restatement of the source's numbers with no arithmetic shown anywhere).

## Dimension 5 — Narrative integrity (anti-reversal)

Check: `hypothesis` explains the observation; `expert_assessment` + `rationale` follow from the post_state measurement; **no field's prose contradicts a computed result anywhere in the episode.** This is the anti-reversal check: compare every verdict-bearing sentence against the numbers it sits next to.

- **2** — gold-03: observation says the old comparator fires at 2.0, the vector table shows exactly that ("old: FIRES"), and the rationale claims only what the table shows. Titles, hypothesis, and judgment all point the same direction as the arithmetic.
- **1** — internally consistent but with a non-sequitur: a rationale that argues from something the measurement doesn't show, while contradicting nothing (e.g. gold-01's rationale citing "13 adjudicated models" would drop here if the episode's own table were removed).
- **0** — any reversal: a case-name/hypothesis/rationale asserting the opposite of the computed verdict (the classic shape, from the calibration record: a title reading "aggregate passes" over a computation reading "VIOLATION ... exceeds permitted 1012 by 88"). One reversal anywhere = 0 for the dimension, however clean the rest reads.

## Dimension 6 — Scope discipline

Check: one episode = one decision. One observation, one chosen intervention, one judgment.

- **2** — gold-01 decides exactly one thing (which tolerance-test method); the fee table, candidates, and measurement all serve that one decision. gold-02 stays disciplined even though its incident sprawled: the citation-identity finding appears only as evidence for the table-source decision, not as a second decision.
- **1** — one nominal decision but the episode smuggles a second (e.g. gold-03 would drop here if it also chose a fixture-coverage policy in the same file); or post_state carries measurements that belong to a different intervention than the chosen one.
- **0** — multiple interventions actually chosen (regardless of the null-marker syntax), or an observation and a chosen_intervention that address different problems.

---

## Grader output format (per episode)

```
file: <path>
validator: EXIT=<n> (<first line of output>)
hard_fail: none | HF-<n> <one line>
D1..D6: <score> <one-line justification each; D3 must show arithmetic>
flags: <every ambiguity you scored 0 on, one line each>
```

No prose beyond this. A grade without the recomputation arithmetic in D3 is itself invalid — regrade.
