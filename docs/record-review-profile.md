# Assay review profile

Follow the shared output contract in [record-reviews.md](record-reviews.md).

Check each METPO term against the exact source commit and distinguish assay classes, phenotype classes, outcome classes and object properties. Verify that the declared relationship describes what the assay measures rather than asserting an organism result. Inspect assay method, target, readout, interpretation, units, controls and limitations against their sources; an ontology definition is not automatically a complete laboratory protocol.

For CMM links, inspect the actual nested target mechanism or capability at its immutable revision and read the evidence for the measured endpoint. Preserve organism, strain, material, chemical form and experimental context where reported. Distinguish bioprocessing yield, chemical transformation and intracellular accumulation from growth or bulk depletion. Missing mappings and protocol information remain explicit gaps.

Review all records changed by the batch and account for excluded candidates. Preserve source licences, source snapshots and append-only history. Source existence and structural validation do not establish scientific support. Confirmed findings become issues and must be fixed and re-reviewed before a user merge decision.
