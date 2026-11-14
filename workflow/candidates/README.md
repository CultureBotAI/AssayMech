# Inert freshness candidate

The four files in `repository-freshness-v1/` are the original 2026-11-10
preparation, with `installed: false` and `adopted: false`. They are outside the
active skill and workflow paths. Do not execute the archived preparation scripts
or interpret this directory as a runtime installation.

The original `proposal.json` remains an accurate historical record: its source
was the reviewed, then-unreleased revision
`02554818325cd77ddfb72a45a26b4d1d76d6b136`. Its historical
`blocked_on_canonical_release` state is not a current publication-status query.

The [separate closeout verification](../../scripts/adhoc/repository-freshness-closeout-20261113/README.md)
checks the actual published `repository-freshness-v1.0.0` tag, release asset and
source tree, exact equality of the candidate payloads to the released source,
merged bootstrap/native dependencies, and preservation of the existing main
files. The [original helper archive](../../scripts/adhoc/repository-freshness-20261110/README.md)
retains preparation evidence and ordering. Neither receipt grants adoption or
execution authority. No active pins, scientific records or site sources change
in this closeout.
