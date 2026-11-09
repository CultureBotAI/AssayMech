"""Input-distinguishing corruption checks against the actual bounded seed."""
from copy import deepcopy
from pathlib import Path

import pytest

from assaymech.seed_audit import audit, load_inputs, locator_value

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def seed_inputs():
    return deepcopy(load_inputs(ROOT))


def test_actual_seed(seed_inputs):
    assert audit(*seed_inputs) == dict(records=9, metpo_role_rows=21, sources=9, cmm_links=4)


@pytest.mark.parametrize("term_id", ["METPO:1007083", "METPO:1000697"])
def test_real_class_cannot_be_assay_identity(seed_inputs, term_id):
    records, _, _, roles, _ = seed_inputs
    record = next(r for r in records if r["id"] == "AssayMech:catalase-test")
    row = next(r for r in roles["rows"] if r["term_id"] == term_id)
    grounding = record["ontology_groundings"][0]
    grounding.update(term_id=term_id, term_name=row["term_name"])
    grounding["evidence"][0]["locator"] = row["source_locator"]
    # Every replaced identifier, label and locator really exists; only its role differs.
    with pytest.raises(ValueError, match="grounding role"):
        audit(*seed_inputs)


def test_real_other_assay_cannot_ground_record(seed_inputs):
    records = seed_inputs[0]
    indole = next(r for r in records if r["id"] == "AssayMech:indole-test")
    catalase = next(r for r in records if r["id"] == "AssayMech:catalase-test")
    catalase["ontology_groundings"] = deepcopy(indole["ontology_groundings"])
    with pytest.raises(ValueError, match="another seed assay"):
        audit(*seed_inputs)


def test_object_property_source_type_is_checked(seed_inputs):
    record = next(r for r in seed_inputs[0] if r["id"] == "AssayMech:ax17-extracted-feii-ferrozine")
    record["ontology_groundings"][0]["entity_type"] = "CLASS"
    with pytest.raises(ValueError, match="entity type"):
        audit(*seed_inputs)


def test_grounding_evidence_must_select_own_real_term(seed_inputs):
    record = next(r for r in seed_inputs[0] if r["id"] == "AssayMech:catalase-test")
    record["ontology_groundings"][0]["evidence"][0]["locator"] = "/graphs/0/nodes/1400"
    with pytest.raises(ValueError, match="own term"):
        audit(*seed_inputs)


def test_cmm_link_cannot_use_another_real_target(seed_inputs):
    records = seed_inputs[0]
    nd = next(r for r in records if r["id"] == "AssayMech:nd-bioleaching-icp-ms")
    fe = next(r for r in records if r["id"] == "AssayMech:ax17-extracted-feii-ferrozine")
    nd["related_records"] = deepcopy(fe["related_records"])
    with pytest.raises(ValueError, match="targets differ"):
        audit(*seed_inputs)


def test_cmm_evidence_must_select_own_target(seed_inputs):
    record = next(r for r in seed_inputs[0] if r["id"] == "AssayMech:ax17-extracted-feii-ferrozine")
    record["related_records"][0]["evidence"][0] = deepcopy(record["related_records"][1]["evidence"][0])
    with pytest.raises(ValueError, match="own target"):
        audit(*seed_inputs)


def test_valid_but_unrelated_primary_study_rejected(seed_inputs):
    records = seed_inputs[0]
    nd = next(r for r in records if r["id"] == "AssayMech:nd-bioleaching-icp-ms")
    bi = next(r for r in records if r["id"] == "AssayMech:fusarium-intracellular-bi-tem-eds")
    nd["method"]["evidence"] = deepcopy(bi["method"]["evidence"])
    with pytest.raises(ValueError, match="different study"):
        audit(*seed_inputs)


def test_primary_license_is_not_inherited_from_cmm(seed_inputs):
    record = next(r for r in seed_inputs[0] if r["id"] == "AssayMech:fusarium-intracellular-bi-tem-eds")
    record["evidence"][0]["source_license"] = "CC-BY-4.0"
    with pytest.raises(ValueError, match="licence differs"):
        audit(*seed_inputs)


@pytest.mark.parametrize("index", ["-1", "01", "-"])
def test_noncanonical_pointer_rejected_even_if_key_retained(index):
    locator = "/graphs/0/nodes/" + index
    with pytest.raises(ValueError, match="canonical"):
        locator_value({"locators": {locator: {"id": "exists"}}}, locator)


def test_cmm_bibliography_must_match_primary_identity(seed_inputs):
    source = seed_inputs[2]["curation/sources/cmm-iron.json"]
    source["locators"]["/sources/2"]["url"] = "https://doi.org/10.1128/AEM.71.2.876-882.2005"
    with pytest.raises(ValueError, match="bibliography"):
        audit(*seed_inputs)


@pytest.mark.parametrize("field", ["description", "method", "measurement", "control"])
def test_concept_field_evidence_selects_own_assay(seed_inputs, field):
    record = next(r for r in seed_inputs[0] if r["id"] == "AssayMech:catalase-test")
    if field == "control":
        # A synthetic fixture exercises the optional field; it is not seed science.
        record["controls"] = [{"description": "Binding-only control fixture.",
                               "evidence": deepcopy(record["evidence"])}]
        entries = record["controls"][0]["evidence"]
    else:
        entries = record["evidence"] if field == "description" else record[field]["evidence"]
    assert audit(*seed_inputs)["records"] == 9
    entries[0]["locator"] = "/graphs/0/nodes/1400"  # Actual indole-test node.
    assert record["ontology_groundings"][0]["term_id"] == "METPO:1007080"
    with pytest.raises(ValueError, match="own assay identity"):
        audit(*seed_inputs)
