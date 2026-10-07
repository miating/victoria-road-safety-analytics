from collections import Counter
from pathlib import Path

import pytest

from src.validation.rules import RULES

ASSESSMENT_DOC = Path(__file__).resolve().parents[1] / "docs" / "data_quality_assessment.md"


def test_rule_ids_are_well_formed():
    assert all(rule.rule_id.startswith("DQ") and rule.rule_id[2:].isdigit() for rule in RULES)


def test_rule_actions_and_stages_are_valid():
    assert {rule.action for rule in RULES} <= {"reject", "fix", "flag"}
    assert {rule.stage for rule in RULES} <= {"staging", "core"}


def test_each_rule_is_checked_once_per_table():
    # audit.dq_check_result uses (run_id, rule_id, table_name) as its primary key.
    duplicates = [key for key, count in Counter((r.rule_id, r.stage, r.table) for r in RULES).items() if count > 1]
    assert duplicates == []


def test_every_rule_is_documented():
    documentation = ASSESSMENT_DOC.read_text(encoding="utf-8")
    undocumented = sorted({rule.rule_id for rule in RULES if f"| {rule.rule_id} |" not in documentation})
    assert undocumented == []


def test_crash_rejections_run_before_orphan_check():
    # DQ16 relies on crashes rejected by DQ01-DQ07 and DQ30 already being in audit.rejected_record.
    order = [rule.rule_id for rule in RULES]
    first_orphan_check = order.index("DQ16")
    for rule in RULES:
        if rule.table == "accident" and rule.action == "reject":
            assert order.index(rule.rule_id) < first_orphan_check


@pytest.mark.integration
@pytest.mark.parametrize("rule", RULES, ids=lambda r: f"{r.rule_id}-{r.table}")
def test_rule_condition_is_valid_sql(rollback, rule):
    # EXPLAIN plans the query without running it, so this is fast.
    rollback.execute(f"EXPLAIN SELECT count(*) FROM {rule.stage}.{rule.table} t WHERE {rule.condition}")
