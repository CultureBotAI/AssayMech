# Released-source verification for the inert candidate

Date: 2026-11-13 local / 2026-11-14 UTC. Issues:
[AssayMech #6](https://github.com/CultureBotAI/AssayMech/issues/6),
[AssayMech #9](https://github.com/CultureBotAI/AssayMech/issues/9) and
[AssayMech #10](https://github.com/CultureBotAI/AssayMech/issues/10).

`verify_release.py` is a read-only verification helper. It compares the actual
GitHub release and Git source objects with the preserved candidate/archive and
the published AssayMech main baseline. Its public result is `verification.json`.
It neither regenerates the four candidate files nor changes their historical
proposal, active governance pin, scientific records, catalogue, workflow or
runtime state. The three original preparation helpers remain unchanged in the
[historical archive](../repository-freshness-20261110/README.md).

The inputs are explicit AssayMech and canonical claw Git roots, an immutable
AssayMech baseline commit, and live public GitHub release/PR/ref/asset metadata.
The output is an audit-only JSON receipt with exact revisions and content hashes;
local root paths and account/configuration details are not output. Verification
fails if the release, source payloads, candidate/archive bytes or preserved
baseline files do not match. The output path must be new, so a fresh observation
does not replace this committed receipt.

The receipt establishes released-source equality and merged upstream
dependencies for this inert repository closeout. It is not an adoption record,
installation instruction or authorization to execute the candidate. The
proposal's original `released: false` and `blocked_on_canonical_release` values
remain the truthful historical observation; current publication evidence is
separate. Active workflow/profile integration and a validated, separately
authorized boundary adoption are still outside this change.

The verifier and its negative-case tests are committed with the receipt they
produced. No packaging edits were made to the three archived helpers. See
`tests/test_freshness_helper_archive.py` for exact original-byte preservation
and `tests/test_freshness_release_verification.py` for verification failure cases.

## Reproduce an observation

Use Python 3.11 or newer, Git and an authenticated `gh` with read access to the
public repositories. Both Git roots must already contain the immutable objects
and enough history for the checked ancestry; the helper never fetches. Pass the
reviewed current main SHA explicitly. The original receipt used
`f7d2d79aa00b6e47816f2f7dea8b418ec084b91e`. If main advances, the old invocation
fails intentionally; inspect the new baseline before making a new observation.

```sh
python scripts/adhoc/repository-freshness-closeout-20261113/verify_release.py \
  --repository-root "$PWD" \
  --canonical-root /absolute/path/to/canonical-claw \
  --base-commit f7d2d79aa00b6e47816f2f7dea8b418ec084b91e \
  --output scripts/adhoc/repository-freshness-closeout-20261113/verification-new.json
uv run --locked pytest -q tests/test_freshness_helper_archive.py tests/test_freshness_release_verification.py
```

Only the new receipt is written. Preserve each existing observation; do not
replace `verification.json` to make an old observation appear current. The
receipt's head is the observed input commit, not a self-referential claim about
the later commit that contains the receipt. Final PR review and checks apply to
that later exact head separately.

The issue #10 regression checks select exact child test nodes to prevent
recursive mutation-runner selection. They remove one guard in fresh-process
memory and require its negative test to fail: the fixed release-audit digest,
tag/source identity, and preservation of published main files. The audit fixture
remains valid JSON with matching asset metadata so it isolates the pinned digest
rather than an unrelated serialization check. No helper file is modified by a
mutation run.
