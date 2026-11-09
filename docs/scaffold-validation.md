# Scaffold validation contract

The publish gate is `just check` plus `just check-vendored`, run after the real
AssayMech bootstrap registration and canonical synchronization. The scaffold
contains no scientific records. Installed-gate results and exact commit checks
are reported in the scaffold PR, separately from the preliminary staged checks.

The native tests cover recursively closed LinkML objects; required evidence and
scope limits; assay identity versus measured phenotype and object property;
immutable source URL/commit/path binding; operational methods and readouts;
canonical JSON Pointer indexes; and distinct CMM mechanisms within one target.
Ontology entity existence, actual term roles and scientific support require
source auditing and independent record review in the seed PR.

Seven isolated fresh-process mutations demonstrate sensitivity to removed
guards: closed schema, ontology type, assay identity, source binding, required
operational method/readout, negative pointer indexes and inventory symlinks.
Staged schema checks use read-only import-map references to existing canonical
schemas; no governed files are copied into staging or treated as installed.

Native history authoring uses the canonical builder and stages both the record
and history sidecar through the shared validated transaction. Native JSON is a
strict YAML subset; the unverified shared fleet serializer remains unavailable.
Tests cover dry-run versus apply, scientific-value round trips, preserved
history, invalid input and the normal creation/editing path.

The inherited writer repair from CofactorMech issue #9 is included from the
start: inventory roots and every record/history path component are checked
before staging or journal creation. Twenty symlink cases cover five directory
positions, internal/external aliases and dry-run/apply. Refusal assertions are
independent of exception wording and also require no record, sidecar or journal
creation. The original writer accepted six internal-history cases: three dry
runs and three applies, with the applies creating files. Fourteen other cases
already refused and are retained as controls, not claimed as newly fixed bugs.

Structural validation cannot establish biological truth. Independent adversarial
review, confirmed-issue fixes, re-review and green hosted checks precede the
user's merge decision. Canonical provider workflows are not invoked by the
native gate, and merge queue automation remains paused.

Installed validation on the bootstrap scaffold passed: `just check` reports
163 passed and three skipped, with zero assay records. The three skips are
canonical skill-frontmatter parameterizations for absent project-local command
files. `just check-vendored` confirms all 22 governed artifacts exactly match
claw revision `89bfcebaee8a0fcf99055b2acd1709abb64f8666`. The installed tests include
all 20 writer-directory cases and normal creation/editing through the real
manifest registration; no synthetic fleet admission was supplied.
