# Freshness preparation helper archive

Date: 2026-11-10. Issue: [AssayMech #6](https://github.com/CultureBotAI/AssayMech/issues/6).

These are the three exact helper scripts used to produce and verify the four
inert candidate files in `workflow/candidates/repository-freshness-v1/` at
`b9e061d831db947af8ef00d67e3230b5c5f715c6`. They were omitted from that result
commit. This follow-up commits the historical helpers alongside those unchanged
results; it does not rerun generation or replace the original evidence.

| Helper | Purpose and inputs | Outputs and effects in the original preparation |
| --- | --- | --- |
| `prepare_consumer.py` | Prepare an explicitly owned consumer using the pinned claw source, repository key/root, scaffold/main/seed revisions and actual ownership map. | Creates an isolated worktree; performs canonical dry run and apply; writes configuration, before, root-map, dry-run, applied and readback evidence. |
| `verify_candidate.py` | Check persisted candidate bytes against pinned Git blobs, candidate schema, original plan, scaffold and evidence directory. | Writes a timestamped verification receipt; checks all scaffold blobs/modes and rejects the proposal as an adoption. |
| `final_inventory.py` | Inventory the original two public consumers, their PRs/checks, review receipts, branches, pins and canonical release observations. | Reads Git/GitHub state and writes the original final handoff; does not merge, queue or activate. |

`provenance.json` binds the original helper SHA-256 values, all four candidate
hashes, exact source/scaffold/result revisions and hashes of retained evidence.
The original helpers and evidence remain under
`~/agent-work/claw/stream-c-freshness-20261110/`; consumer evidence remains under
`~/agent-work/CofactorMech/freshness-20261110/evidence/` and
`~/agent-work/AssayMech/freshness-20261110/evidence/`. The original canary receipt
and Assay start receipt preserve the completed Cofactor-before-Assay generation
order. This archive correction does not rewrite those observations. The Assay archive
correction began only after Cofactor correction head
`afefd3b4be5f605c4a658666056f2fc3c6251bae` completed independent review and
green hosted checks; `correction_order` records that separate sequence.

## Historical execution limits

These files are an audit archive, not portable current rollout commands. No
helper packaging or behavior edits were made. They retain the original absolute
host paths, expected revisions, environment and output locations. The canonical
source was the reviewed, unreleased PR revision recorded in the manifest; no
release/adoption readiness is asserted. `prepare_consumer.py` creates state and
calls the original generator's apply mode. The other two scripts execute their
checks and evidence writes even on import. Do not run or import these archives
as part of installation, CI, activation or a new generation attempt.

`verify_candidate.py` intentionally accepts only the original candidate-only
diff. `final_inventory.py` intentionally requires four PR files and the original
heads, so neither is a verifier for this expanded PR. These historical guards
have not been weakened. For this correction, run the offline integrity checks:

```sh
uv run --locked pytest -q tests/test_freshness_helper_archive.py
```

Those checks read bytes without importing or executing archived code. They bind
all three exact originals and all four unchanged candidates to the recorded
hashes and fail when an archive is missing or changed. Native repository checks
remain required. The historical archive correction added four candidate files
plus three archived helpers, this README, provenance JSON and the integrity
test. The current closeout also includes the separate release verification
helper, its receipt, tests and documentation linked below.

The public additions were inspected for secrets, email addresses and unrelated
private-repository data. The two-consumer inventory remains intact because both
consumers are within the original public preparation scope. No credentials,
private repository data or raw environment/configuration dumps are included.

## Current closeout (2026-11-13 local; 2026-11-14 UTC)

[AssayMech #9](https://github.com/CultureBotAI/AssayMech/issues/9) corrects the
old present-tense scaffold, unpublished-source and scheduling dependency claims.
The scaffold and seed are on published main, and this branch incorporates
`f7d2d79aa00b6e47816f2f7dea8b418ec084b91e`, including the catalogue. Canonical
claw PR #1128 was released as `repository-freshness-v1.0.0` from
`e43afbf92e7ae0265943ca8a237efe07ecf074fb`; the native adapter PR #1165 merged
at `59ad5327c4ba979254e018c51f180505e1f515a4`. These are verified separately in
[the closeout receipt](../repository-freshness-closeout-20261113/README.md).

The original proposal correctly describes its preparation against an unreleased
revision. Its four files, this archive's three helper scripts and provenance
JSON remain unchanged. Released payload equality is additional evidence; it
does not retroactively change the original source or turn this candidate into
an adoption. Historical host paths and preparation-order receipts are retained.

No scaffold or canonical-publication dependency remains for this inert
repository change. Active workflow/profile integration, boundary adoption and
runtime execution still require separate authorization and validation. The
archive and the new verification receipt grant no execution authority.
