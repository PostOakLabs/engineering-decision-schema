# Gold episodes — calibration anchors, not templates

These three files are the calibration layer for the episode-corpus factory: mass-drafted episodes are graded against `GRADING-RUBRIC.md`, whose 0/1/2 anchors cite these files as the worked examples. They deliberately span the provenance enum — `gold-01` reproduced (TRID mixed-direction tolerance recompute), `gold-02` retrospective (a real wrong-table incident with its record hashes), `gold-03` synthetic-fixture (epsilon-sign boundary construction).

**Gold means anchor, never target.** Drafters must NOT copy these episodes' domains, numbers, or phrasing — a drafted episode resembling a gold file verbatim is a defect, not a compliment. What generalizes is the shape: concrete costs in every `rejected_because`, measurements recomputable from stated inputs, provenance labels that match the evidence trail, one decision per episode.

Non-silicon mapping convention used here (the schema's `design`/`environment` fields are silicon-flavored): `design.pdk` carries the governing framework (the "process kit" of a regulatory computation), `rtl_commit`/`pdk_commit` pin the computed artifact's source record and the rulebook snapshot (sha256 or document id), and a reproduced episode's `environment` tool-version fields state `n/a-non-silicon-episode` honestly rather than fabricating versions, with the actual recompute environment in `container`. `failure_class` uses `FAIL_FLOW` for methodology/computation defects.

Every file here validates `EXIT=0` against `python -m edi_schema.cli` as-is; anything that stops validating is a regression, not a schema problem.
