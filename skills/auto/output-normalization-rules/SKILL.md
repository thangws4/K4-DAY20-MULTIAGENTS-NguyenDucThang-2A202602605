---
name: output-normalization-rules
description: Use when a task requires transforming or aggregating records into a structured output with naming, ordering, or schema conventions.
---
Normalize and order output fields according to the stated conventions before writing the artifact.

1. Extract every naming, ordering, and schema rule from the task prompt and any conventions document.
2. Normalize identifier fields to the required form (e.g. lower-case with `-` replaced by `_`).
3. Sort collections by the exact required keys and direction (e.g. by service, then by timestamp ascending).
4. Include required top-level metadata exactly as specified (e.g. `schema_version` and `generated_by` with their required values).
5. Verify counts and aggregates are internally consistent (totals match the sum of their parts).
6. Self-check: re-read each rule and confirm the written output satisfies it literally, including field names, casing, and ordering.
