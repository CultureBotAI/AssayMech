# Initial assay seed: scope and provenance

The seed contains nine records: six named METPO assay concepts and three
operational assays drawn from primary CMM literature. There are no imported
organism-level test results. Four links identify selected mechanisms in four
CMM records; the iron and ferrihydrite links describe the same Ax17 experiment.

| Records | Grounding | What the record establishes |
| --- | --- | --- |
| Indole, methyl red, Voges-Proskauer, catalase, oxidase, urease | Six METPO assay parent classes | Assay identity and available conceptual method/readout; no organism outcome or complete protocol |
| Nd bioleachate ICP-MS | Explicit METPO gap; CMM neodymium mechanism | Filtered-leachate Nd in a laboratory synthetic-phosphate experiment |
| Ax17 extracted Fe(II) ferrozine | METPO reduces object property; CMM iron and ferrihydrite mechanisms | Extraction-defined Fe(II), with abiotic controls; no mineral identity |
| Fusarium intracellular Bi TEM-EDS | METPO accumulates object property; CMM bismuth mechanism | Intracellular elemental localization; no bulk uptake capacity or molecular-phase assignment |

`ASSAY_IDENTITY` is reserved for the six selected assay classes. Positive and
negative outcome classes are distinct entities. The Gram-stain node is a
phenotype, while `reduces` and `accumulates` are object properties. A process
predicate can be tested by an assay; it is not that assay's identity.
The 21-row METPO inventory retains all six selected parents, their twelve
outcome classes, the Gram-stain phenotype and the two process predicates. It
is a bounded selection and does not claim to catalogue every assay in METPO.

## Immutable repository sources

METPO is pinned to commit `800c9d27913158efdf466edf2cd710dbf1ce893f` of
`berkeleybop/metpo`, using `metpo.json`. This is a commit pin, not a claim
that the ontology was released on that commit date. The latest release observed
during source discovery was `2026-06-12`; the seed cites the exact chosen commit
at every grounding. Source nodes retain original JSON Pointer indices. The
source JSON represents object properties with `type: PROPERTY` and
`propertyType: OBJECT`; the assay schema represents that pair as
`OBJECT_PROPERTY`.

CMMMech is pinned to current main observed during discovery,
`df061de720fb9884dcc6e41369a3049cef52a059`. Repository identity was resolved
through CLAW's `RepositorySettings`. An untruncated GitHub tree and all 698
record paths were inspected at that commit through a read-only snapshot. The
local checkout was not treated as current main. The selected source projections
retain parent IDs, exact mechanism indices, mechanism fields and cited source
bibliography. Unused protein examples are deliberately omitted. No endpoint is
inferred from a material name alone.

## Primary-method boundaries

Marecos 2025 is the publisher article at DOI `10.1038/s42003-025-08061-4`,
section `Sec16`, and Supplementary Data 4, sheet `4A`, cell `B2`. The study's
reported mass-normalized response is labelled micrograms Nd per gram NdPO4.
It is not a recovered fraction. Mon2 contains monazite-Nd and rhabdophane-Nd;
the assay does not reinterpret it as pure monazite. Filtration occurs after
leaching; the paper does not establish that the contacting lixiviant is
cell-free. Failed Europe PMC and CAPTCHA fetches are excluded from the source
catalogue; the successful publisher HTML and supplemental workbook supplied
the retained digests.

Sklute 2023 is DOI `10.3389/fmicb.2023.1272245`, Methods and Results sections
`s2` and `s3`. Oxalate dissolution precedes ferrozine measurement. The Methods
specifies 0.22 micrometre filtration before dissolution; the Results uses
0.2 micrometre wording. The record preserves that limitation rather than
silently reconciling it. Fe(II) supplementation and cysteine require the matched
uninoculated controls. Mineral identity requires other analyses.

Dodge and Wackett 2005 is DOI `10.1128/AEM.71.2.876-882.2005`, PMC546758,
sections `sec7` and `sec15`. The microscopy preparations use 96-hour cultures
and approximately 60 nm sections. Salicylate-grown control granules lack
detected Bi in the reported comparison. The beam spot is larger than a
granule, and localization neither establishes a unique Bi compound nor
quantifies whole-biomass uptake. This record does not conflate the microscopy
assay with the paper's separate soluble-Bi time course.

## Offline checks and their limits

`curation/source-catalogue.json` records original-byte SHA256 values, source
URLs, immutable repository pins, projection hashes and rights provenance.
`curation/sources/` contains compact selected-source projections. METPO and CMM
objects preserve source fields; article projections are explicitly curator
paraphrases with precise HTML or worksheet locators. Full paper HTML and the
original workbook remain in durable private research state outside this
repository. Their digests make the reviewed input explicit; projection hashes
check local integrity, not remote authenticity.

`just audit-seed` runs offline. It checks the reviewed initial identity set,
source roles, exact term/target evidence binding, CMM bibliography-to-primary-
study correspondence, source licences, selected study scopes and source
projection hashes. It rejects real outcome/phenotype classes used as assay
identity, unrelated valid study citations, substituted CMM targets and
noncanonical JSON Pointer indices. It does not prove that prose is scientifically
correct or that a protocol is complete. Independent scientific review must
consult the cited original sources; the retained paraphrases are not independent
evidence of their own accuracy. New seed scope requires deliberate extension
of the reviewed inventory and the audit contract.

Data attribution and source-specific rights are in `LICENSE-DATA`. Neither a
CMM data license nor AssayMech's annotation license is inherited by a cited
primary paper. The Dodge article has no established CC license in this seed.
