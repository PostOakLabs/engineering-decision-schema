# Examples

Everything in this directory is **validator food**. None of it is data.

The repository rule is that measurements and expert judgments are never
invented. Two mechanisms keep that honest, and both are used here:

1. **`TODO(expert)` / `TODO(maintainer)` markers** sit in every field that is a human
   judgment. A document still containing one is a draft.
2. **`"provenance": "synthetic-fixture"`** flags a file that is schema-valid but
   carries no real observation. Its `workload_id` (for reports) says
   so out loud.

## What each file is

| File | Kind | Flag |
|---|---|---|
| `episode.retrospective.example.json` | episode | Every judgment field is a `TODO(expert)` marker. |
| `episode.reproduced.example.json` | episode | `provenance: synthetic-fixture`. |
| `run-manifest.example.json` | run-manifest | `run_id: RUN_FIXTURE`; every pin is a `FIXTURE-` placeholder. |
| `zkprof-report.example.json` | report | `workload_id: fixture-not-a-measurement`. |

One file per document kind, so `edi-validate examples/*.json` exercises all
three schemas (episode / run-manifest / report) every time CI runs it.

## Sentinels you will see

- Numeric values are chosen to be visibly illustrative (repeated digits:
  `111111.0`, `222222.0`, `11111`) so no one mistakes them for a measurement.
  They live only inside `synthetic-fixture` documents, where that is permitted.
- Tool versions and commit ids read `FIXTURE-not-a-real-version` /
  `FIXTURE-not-a-real-commit`. Nothing here pins a real environment.

## Enum-constrained fields cannot hold a TODO string

`severity`, `expert_assessment` and `confidence` are constrained by the schema
to an enum or a number, so a `TODO(expert)` marker cannot be placed inside them
without making the document schema-invalid. In examples these carry **neutral
sentinels that mean "not assessed"**:

- `"expert_assessment": "inconclusive"`
- `"confidence": 0.0`

They are placeholders, not judgments. `severity` is likewise a placeholder.
The episode scaffolder in `openeda-decision-dataset` faces the same tension.

## Validating

```bash
edi-validate examples/*.json
```

All three document kinds must pass (episode / run-manifest / report).
