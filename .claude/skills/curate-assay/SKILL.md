---
name: curate-assay
description: "Curate a microbial or critical-materials assay with exact METPO grounding and scoped measurement evidence."
---

Read `AGENTS.md` and the source record. Verify the issuing METPO entity at the cited immutable commit. Keep assay identity, measured phenotype and tested object property distinct. An assay description never establishes a positive or negative result for an organism.

Read authoritative method and measurement sources. Include protocol details, units and controls only when established; state limitations and gaps explicitly. Inspect every CMM target record and nested mechanism locator at the cited commit. Require evidence for the assay's measured process within its organism and material scope, not merely a shared chemical name.

Prepare the complete record, then use `just new-history` in dry-run mode followed by the authorized apply. Run `just check` and `just check-vendored`. For scientific review, follow `docs/record-reviews.md` and `docs/record-review-profile.md`, and persist the validated bundle through `scripts/record_review.py`; prose alone is not a completed structured review. Independent PR review and user merge decisions remain separate.
