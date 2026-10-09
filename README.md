# edi-schema

Shared JSON Schemas and validation for engineering-decision artifacts.

This repository holds the one artifact that several downstream repositories
depend on: three JSON Schemas (draft 2020-12) and a small Python package that
validates documents against them, including the rules JSON Schema cannot
express on its own.

It is deliberately tiny and boring. It contains no data.

## The three document kinds

| Kind | Schema | What it captures |
|---|---|---|
| `episode` | `schemas/episode.schema.json` | One expert decision: the state before, what was observed, what was considered *and rejected*, what was done, the state after, and the judgment. |
| `manifest` | `schemas/run-manifest.schema.json` | One reproducible run: design and PDK commits, tool versions, and sha256 of the inputs. |
| `report` | `schemas/zkprof-report.schema.json` | One profiling run of a proving workload: primitive-level timing attribution plus the deployment context it was measured under. |

## Install

Pinned by git tag. The package is not on a package index, so consumers
reference the tag directly:

```bash
pip install "git+https://github.com/PostOakLabs/engineering-decision-schema@v0.5.0"
```

For local development, from a checkout:

```bash
pip install -e ".[dev]"
```

Requires Python 3.11 or newer. The only runtime dependency is `jsonschema`.

## CLI

```bash
edi-validate examples/*.json            # infer kind per file
edi-validate --type episode episode.json
edi-validate --json bad.json            # machine-readable errors
```

The kind is inferred from the document's `$schema` key, then from its shape;
`--type` overrides both.

| Exit code | Meaning |
|---|---|
| 0 | every document validated |
| 1 | at least one document failed validation |
| 2 | usage or IO problem: unreadable file, malformed JSON, undetectable kind |

Output is one line per error, each carrying a code, a path, and a message:

```
$ edi-validate mutated.json
mutated.json [episode]
2 error(s):
  - schema:required at $: 'rationale' is a required property
  - E_CANDIDATES_MULTIPLE_CHOSEN at $.candidates_considered: 2 candidates have rejected_because: null (at [0], [1]); exactly one must be the chosen intervention
```

Errors are sorted by document path, so the output reads top-to-bottom through
the file.

## Library API

Every validator takes a decoded Python object and returns a list of `Error`.
An empty list means valid. Nothing raises on invalid input.

```python
from edi_schema import validate_episode, validate_report, validate_manifest

errors = validate_episode(document)
if errors:
    for err in errors:
        print(err.code, err.path, err.message)
```

`validate(document, kind=None)` dispatches on an explicit kind, or infers one.

## Rules JSON Schema cannot express

These live in the Python validator and each carries its own error code.

| Code | Rule |
|---|---|
| `E_CANDIDATES_NO_CHOSEN` | No entry in `candidates_considered` has `rejected_because: null`. |
| `E_CANDIDATES_MULTIPLE_CHOSEN` | More than one does. Exactly one candidate is the chosen intervention. |
| `E_PROVENANCE_REPRODUCED_REQUIRES_ENVIRONMENT` | `provenance: reproduced` with no `environment` block. |
| `E_PROVENANCE_REPRODUCED_REQUIRES_RTL_COMMIT` / `..._PDK_COMMIT` | `provenance: reproduced` without pinned commits. |
| `E_SHARE_SUM_PRIMITIVES` | Report `primitives[].share` does not sum to `1.0 ± 0.02`. |
| `E_STARTED_AT_NOT_ISO8601` | Manifest `started_at` is not an ISO 8601 date-time. |
| `E_STARTED_AT_NO_TIMEZONE` | It parses but carries no offset, so runs from different zones cannot be ordered. |

The `reproduced` coupling is also expressed as an `if/then` inside the schema,
for consumers that read the schema directly rather than through this package.

Phase shares are intentionally *not* checked: phases may nest or overlap and
need not partition `total_ms`. Primitive attribution must partition it.

## Conventions these schemas enforce

- **Units live in key names.** `wns_ns`, `wirelength_um`. Not in a sibling field.
- **Absent means not measured.** A metric that was not captured at a stage is
  omitted, never written as `0`.
- **Enum-constrained fields cannot hold a TODO marker.** `severity`,
  `expert_assessment` and `confidence` are enums or numbers. In examples they
  carry neutral sentinels (`"inconclusive"`, `0.0`) that mean "not assessed".
  See [`examples/README.md`](examples/README.md).
- **Nothing here is data.** Every file under `examples/` is validator food.
  Fixtures say so: `"provenance": "synthetic-fixture"` for episodes,
  `"workload_id": "fixture-not-a-measurement"` for reports. A test fails the
  build if any example ever claims `provenance: "reproduced"`, because no run
  produced it.
- **The tool is LibreLane** (not "OpenLane"), and its P&R engine is OpenROAD.
  The `environment` block records versions under those names.

## Consuming the schemas from another language

Read the files from `schemas/` directly, or resolve them through the package:

```python
from edi_schema import schema_path

schema_path("episode")  # -> Path to episode.schema.json
```

Schema lookup order is: `$EDI_SCHEMA_DIR`, the copy bundled into an installed
wheel, then a `schemas/` directory found by walking up from the package (which
is what makes an editable install work without duplicating files). CI asserts
the wheel really does bundle all three.

Pin the tag you consume and record it. Re-points to a moving branch make run
manifests unreproducible.

## Development

```bash
pip install -e ".[dev]"
pytest                    # the count is derived by running it; not hand-pinned
ruff check .
ruff format --check .
```

CI runs lint and tests on Python 3.11, 3.12 and 3.13, validates the committed
examples through the installed CLI, and checks that a built wheel still carries
the schemas.

## License

The code is Apache-2.0; see [LICENSE](LICENSE). The episode corpus / fixture
data that `edi-croissant` exports is **CC BY 4.0** (licensing decision of
2026-09-02), which is distinct from the code license. The split is recorded in
[NOTICE](NOTICE).
