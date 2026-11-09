# AssayMech

AssayMech curates evidence-backed assay concepts and measurement methods for microbial characterization and critical-materials bioprocessing, biotransformation and bioaccumulation. The scaffold contains no scientific seed records; source-reviewed records arrive in a separate PR.

METPO is the ontology seed source. Each mapping names the exact METPO term, entity type, source commit and file. Named tests, measured phenotypes and tested object properties have different relationships to an assay. A catalase-test definition does not establish a positive result for an organism, and an accumulation predicate is not an assay identity.

Operational assays record a sourced method, measured target, readout and scope limits. Units, controls and protocol parameters are included only when supported. CMMMech links identify a particular mechanism or capability at a pinned revision and source locator; the assay does not generalize an experimental endpoint to every organism or material. Missing mappings and protocol details remain explicit research gaps.

## Development

Install [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/), then run:

```sh
uv sync --locked
just check
just check-vendored
```

`just check` runs the same native lint, schema, records, history and test gate used in CI. `just check-vendored` verifies governed files against the immutable claw commit in `scripts/.vendored_canon_ref` and needs public GitHub access. The required `validate-strict` job runs both recipes on every pull request, push and merge group.

Records live at `data/assays/<slug>.yaml`. The installed LinkML schema is `src/assaymech/schema/assaymech.yaml`. Validation rejects unknown fields throughout the document, incompatible ontology entity types, unbound source URLs, ambiguous source locators and inconsistent history. These checks do not establish source truth: curators still verify the cited ontology entities, methods and target evidence.

For a new or updated record, prepare a YAML input outside `data/` and use:

```sh
just new-history --record data/assays/example.yaml --input workspace/example.yaml --summary "Describe the change" --details "Sources inspected and what changed" --actor curator
just new-history --record data/assays/example.yaml --input workspace/example.yaml --summary "Describe the change" --details "Sources inspected and what changed" --actor curator --apply
```

The first command validates a dry run. Apply records a canonical history sidecar and matching inline event in one validated transaction; existing history is preserved. Use `--action CREATE` for a new record. Git identity is checked, writes use the repository lock and recovery journals remain under `workspace/write-journals/`.

## Governance and release state

The bootstrap governance pin is an immutable published claw onboarding-branch commit. Local registration and passing repository checks do not complete the fleet release: the shared-pin rollout and committed-main fleet audit remain separate release gates. The claw dependency, `uv.lock` and governed pin must move together on future re-pins.

Each PR receives independent review, issue fixes, re-review and green checks before the user decides whether to merge. Merge queue automation is paused. Retained work and review evidence live under `~/agent-work/AssayMech/`; push committed work the same day.

Original code and schemas are CC0. Scientific records are CC-BY-4.0 with source attribution; imported and governed files retain their own licences and notices. The native history command writes deterministic JSON, a strict subset of YAML. Shared `kg_microbe_write.dump_record` intentionally refuses the unverified fleet serialization profile; the native writer owns this representation and does not authorize general cross-corpus reserialization.
