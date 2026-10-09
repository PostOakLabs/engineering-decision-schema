# DESIGN-RATIONALE — episode schema

This doc grounds the episode schema's three core design bets in the 2026
process-supervision literature. It is a design-rationale record, not a
literature review: every load-bearing claim carries a verbatim quote with a
locator and a URL, or is explicitly marked as having no literature anchor.

Scope and honesty rule

- Papers were retrieved and read in full on 2026-08-31. Quotes are verbatim
  from the retrieved HTML/PDF text.
- Where a paper's actual finding does not directly support a schema field, the
  row says so. No citation is stretched to fit a field it does not speak to.
- The "no literature anchor" value is used for fields whose justification is
  schema engineering or practitioner judgment rather than an empirical result.

## The three bets

1. Candidates-with-rejections: a `candidates_considered` array in which every
   intervention is kept and exactly one entry carries `rejected_because: null`
   (the chosen one).
2. Failure-weighting: failures are recorded and distinguished from successes so
   a downstream consumer can weight them; failures are not silently dropped.
3. Process-level annotation: the record captures the decision at the flow-stage
   (process) level, not only the final outcome.

## Field-by-field rationale

| Schema field | Design choice (bet) | Supporting citation / anchor |
|---|---|---|
| `candidates_considered[].intervention` and `.rejected_because` | Keep every considered intervention, including rejected ones; the rejection reason is retained rather than the candidate being discarded (bet 1, and part of bet 2). | OpenThoughts, §4.5 "Answer Filtering", Table 7 caption: "Filtering answers did not improve over not filtering at all. Using verification techniques such as majority consensus filtering or response-length-based filtering did not improve upon training on all samples." |
| `candidates_considered` (array) | Do not reduce the candidate set by dropping the rejected entries. | OpenThoughts, §4.5: "across all domains, the no-filtering strategy (training on all samples without controlling compute) led to performance similar to that of all other methods of filtering. This result suggests that the benefits of answer filtering are not significant enough to justify reducing the number of samples in the dataset, regardless of the domain." Takeaway: "We do not perform answer filtering because no filtering strategy outperformed the baseline, which uses all the answers." |
| `candidates_considered` exactly-one-`null` (enforced in Python as `E_CANDIDATES_NO_CHOSEN` / `E_CANDIDATES_MULTIPLE_CHOSEN`; not expressible in JSON Schema) | Enforce a single chosen candidate via a cross-field pointer. | No literature anchor. This is a schema-engineering invariant. The retained-rejected-candidate array is the EDI thesis itself and has no equivalent model in either paper. |
| `failure_class` (enum) | Enumerate the physical-design failure mode so it can be used as a weighting key. | No literature anchor. Neither paper defines a failure-taxonomy enum; OpenThoughts does not use an EDA failure taxonomy. |
| `expert_assessment` (preferred / acceptable / regretted / inconclusive) | Capture a graded post-hoc verdict on the chosen intervention, not just binary success. | No literature anchor. ICCS 2026 scores output correctness as a binary judge decision ("output a binary decision", §2.4) and scores steps on FVCU; it does not grade a global "regretted" verdict. The verdict scale is practitioner judgment. |
| `confidence` (0..1) | Numeric self-assessed confidence in this decision. | No literature anchor. Neither paper defines a scalar confidence field. |
| `observation.severity` (blocking / degrading / cosmetic) | Triage how much the observed deviation matters. | No literature anchor. Neither paper uses a severity triage. |
| `prior_state` / `post_state` (each with `stage`) | Record the state before and after the decision at a flow-stage granularity, rather than only the final outcome (bet 3). | ICCS 2026, §3.1 (Model-based Metrics): "Atomizer: Decomposes raw reasoning traces into atomic steps using a strict verbatim extraction strategy. This preserves the original density and style of the text, aligning with process supervision standards [22]." Also §3.1, Coherence: "Checks if the step logically follows the preceding one without gaps, satisfying the Markov property of the chain." |
| `observation` (metric / value / target) | Record the measured deviation and the target it was measured against, at the point of decision. | No literature anchor in the specific metric/value/target sense. The ICCS process-supervision framing (above) supports annotating at step granularity, but neither paper specifies recording an observed metric value and its target. Marked no literature anchor to avoid stretching. |
| `hypothesis` / `rationale` / `chosen_intervention` (parameter / before / after) | Keep the causal reading of the observation and why the chosen intervention was preferred, i.e. the reasoning, not only the final outcome (bet 3). | ICCS 2026, §3.1, Validity: "Evaluates the mathematical and inferential correctness of the derivation. It distinguishes between calculation errors and logical fallacies." And §3.1 opening: "To assess the intrinsic quality of the reasoning steps beyond binary correctness, we implement an automated evaluation pipeline based on the FVCU taxonomy (Factuality, Validity, Coherence, Utility)." Also OpenThoughts, Appendix H.3: "removing self-reflection leads to an average relative performance drop of 49.1% across diverse downstream benchmarks. These findings suggest that self-reflection and long-form reasoning structures are essential for enhancing the reasoning capabilities of OpenThoughts3 models." |

## Notes on the anchors

Rejected candidates / discard-vs-keep (bet 1). The strongest available finding is
OpenThoughts §4.5, which shows that removing candidate answers via verification,
majority consensus, or response-length filtering does not beat keeping all
samples. This supports not discarding rejected candidates. Caveat, stated
honestly: OpenThoughts operates on SFT per-answer filtering and has no
retained-candidate array; the finding is a signal about "do not drop failures",
not a specification of a `candidates_considered` structure. The additional
OpenThoughts Appendix H.1.2 finding ("Removing proofs degrades performance on
relevant benchmarks despite being unverifiable with our methodology") supports
keeping hard-to-verify examples as well.

Failure-weighting (bet 2). There is no direct literature anchor for the specific
weighting scheme this schema enables. The OpenThoughts §4.5 result is a signal
that a simple success/failure re-weighting or filter does not buy gains, so any
weighting must be justified rather than assumed. The ICCS 2026 scale-dependence
finding complicates a single universal weight: a verbose (redundant) trace is
helpful to a larger model and neutral or harmful to a smaller one (RQ2:
"This indicates that the larger model benefit from verbose, rigorous derivation
steps, even if repetitive, rather than smooth narrative explanations."). No
concrete numeric weighting rule is present in either paper, so the weighting
scheme should be treated as practitioner judgment until measured.

Process-level annotation (bet 3). ICCS 2026 is the direct anchor: it decomposes
traces into atomic steps and judges each step (FVCU), while explicitly
separating that from a binary final-answer judgment used only for evaluation
(§2.4: "The judge was strictly prompted to assess the correctness of the final
answer (ignoring intermediate reasoning steps) against the ground truth.").
OpenThoughts Appendix H.3 independently shows that removing intermediate
self-reflection hurts performance, which supports keeping the process, not just
the outcome.

## Fields with no literature anchor

The following are justified by schema engineering or practitioner judgment, not
by either paper: the exactly-one-`null` invariant inside `candidates_considered`,
the `failure_class` enum, the `expert_assessment` enum, the `confidence` scalar,
the `severity` enum, and the `observation` metric/value/target shape.

## TODO(expert)

- Confirm the failure-weighting scheme. Neither paper specifies a numeric
  weighting rule; the OpenThoughts §4.5 result suggests filtering/re-weighting
  gains are marginal, but it does not define what weight to apply. Decide
  whether a numeric weight belongs on the schema or is derived downstream.
- Review the ICCS 2026 (not ICLR 2026) sourcing. The second paper is an ICCS
  2026 paper, not an ICLR 2026 paper as originally expected (see Sources). If
  only ICLR-anchored citations are acceptable, bet 3 currently relies on an
  ICCS 2026 anchor.

## TODO(maintainer)

- Confirm whether `severity` and `expert_assessment` should stay as enums given
  they can never carry a literal `TODO(...)` marker (see HANDOFF §4), and whether
  that interacts with the process-level annotation bet's intent to record
  "unfinished" steps.

## Sources

1. Guha, E., Marten, R., Keh, S., Raoof, N., Smyrnis, G., Bansal, H., Nezhurina,
   M., Mercat, J., Vu, T., Sprague, Z., Suvarna, A., Feuer, B., Chen, L., Khan,
   Z., Frankel, E., Grover, S., Choi, C., Muennighoff, N., Su, S., Zhao, W.,
   Yang, J., Pimpalgaonkar, S., Sharma, K., Ji, C. C.-J., Deng, Y., Pratt, S.,
   Ramanujan, V., Saad-Falcon, J., Li, J., Dave, A., Albalak, A., Arora, K.,
   Wulfe, B., Hegde, C., Durrett, G., Oh, S., Bansal, M., Gabriel, S., Grover,
   A., Chang, K.-W., Shankar, V., Gokaslan, A., Merrill, M. A., Hashimoto, T.,
   Choi, Y., Jitsev, J., Heckel, R., Sathiamoorthy, M., Dimakis, A. G., and
   Schmidt, L. "OpenThoughts: Data Recipes for Reasoning Models." ICLR 2026
   (Oral). OpenReview forum id=7xjoTuaNmN; arXiv:2506.04178v1. Retrieved
   2026-08-31. https://openreview.net/forum?id=7xjoTuaNmN
   (https://arxiv.org/html/2506.04178v1)

2. Langner, M., Pihulski, D., Eliasz, J., Rajkowski, M., Kazienko, P., Piasecki,
   M., Kocoń, J., and Ferdinan, T. "What properties of reasoning supervision are
   associated with improved downstream model quality?" To appear in the
   Proceedings of the International Conference on Computational Science (ICCS)
   2026. arXiv:2605.13290. Retrieved 2026-08-31.
   https://arxiv.org/abs/2605.13290 (https://arxiv.org/html/2605.13290v1)
