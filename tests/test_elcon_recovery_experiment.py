"""Runner and assessor checks for the frozen ElCon-EE 2027 protocol v1.0.

All outputs go to tmp_path; these tests never write under research/elcon2027/results.
"""

import csv
import dataclasses
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.integration import recovery_experiment as rx
from app.integration.maintenance_effect_service import EffectLedger
from app.integration.recovery_policies import Evidence, Observation, p_capability_aware


@pytest.fixture(scope="module")
def oracle():
    return rx.load_oracle()


def _case(oracle, case_id):
    return next(c for c in oracle["cases"] + oracle["stress_cases"] if c["id"] == case_id)


def test_frozen_protocol_verifies_against_manifest_and_service_hash():
    frozen = rx.verify_frozen_protocol()
    assert set(frozen["protocol_files"]) == {
        "README.md",
        "protocol.md",
        "oracle_table.json",
        "service_review.md",
    }


def test_tampered_oracle_is_refused(tmp_path):
    protocol = tmp_path / "protocol"
    shutil.copytree(rx.PROTOCOL_DIR, protocol)
    oracle_path = protocol / "oracle_table.json"
    oracle_path.write_text(oracle_path.read_text().replace('"C09"', '"C09x"'))
    with pytest.raises(rx.ProtocolMismatch, match="oracle_table.json"):
        rx.verify_frozen_protocol(protocol)


def test_modified_service_is_refused(tmp_path):
    repo = tmp_path / "repo"
    service = repo / rx.FROZEN_SERVICE
    service.parent.mkdir(parents=True)
    service.write_text((rx.REPO_ROOT / rx.FROZEN_SERVICE).read_text() + "\n# drift\n")
    with pytest.raises(rx.ProtocolMismatch, match="maintenance_effect_service"):
        rx.verify_frozen_protocol(rx.PROTOCOL_DIR, repo_root=repo)


def test_existing_run_directory_is_never_overwritten(tmp_path):
    (tmp_path / "run-1").mkdir()
    with pytest.raises(FileExistsError):
        rx.run_experiment(
            run_id="run-1", results_root=tmp_path, replays=1, pipeline=False, scratch_root=tmp_path / "s"
        )


def test_policy_receives_only_observation_and_evidence(tmp_path, oracle, monkeypatch):
    seen = []

    def spy(obs, ev):
        seen.append((obs, ev))
        return p_capability_aware(obs, ev)

    monkeypatch.setitem(rx.POLICIES, "P", spy)
    case = _case(oracle, "C08b")
    rx.run_trial(case, "P", oracle, tmp_path)

    assert seen and {(type(o), type(e)) for o, e in seen} == {(Observation, Evidence)}
    # The values passed in carry no case label, fault mechanism or hidden timing.
    for o, e in seen:
        text = repr(o) + repr(e)
        for token in ("C08b", "F5v", "visibility_delay", "fault", str(tmp_path)):
            assert token not in text, token
    forbidden = {"case_id", "fault", "fault_schedule", "ledger", "oracle", "expected"}
    assert not {f.name for f in dataclasses.fields(Observation)} & forbidden


def test_revalidation_genuinely_runs_governance_agent(tmp_path, oracle):
    raw = rx.run_trial(_case(oracle, "C03"), "B1", oracle, tmp_path)
    resumer = raw["resumers"][0]
    assert resumer["governance"] == "ALLOW"
    assert resumer["revalidation_provenance"].startswith("GovernanceAgent re-run")


def test_assessor_takes_effects_from_ledger_not_self_report(tmp_path, oracle):
    case = _case(oracle, "C03")
    raw = rx.run_trial(case, "B0", oracle, tmp_path)
    raw["resumers"][0]["complete"] = True  # a self-report cannot make it complete
    row = rx.assess_trial(raw, case)
    ledger = EffectLedger(raw["ledger_db"])
    op = f"{rx.WORKFLOW_ID}:{rx.STEP_ID}"
    assert row["committed_effects"] == ledger.committed_effect_count(op) == 2
    assert row["duplicate_effect"] is True
    assert row["completed"] is False
    assert row["oracle_valid"] is False


def test_protocol_violation_hold_is_an_error_not_a_hold(tmp_path, oracle, monkeypatch):
    from app.integration.recovery_policies import Action

    monkeypatch.setitem(rx.POLICIES, "P", lambda o, e: Action("QUERY"))
    case = _case(oracle, "C05")  # outcome query unavailable
    row = rx.assess_trial(rx.run_trial(case, "P", oracle, tmp_path), case)
    assert row["policy_errors"] == "query_rejected_unavailable"
    assert row["holds"] == 0
    assert row["oracle_valid"] is False
    assert row["workflow_status"] == "policy_error"


def test_non_allow_revalidation_makes_hold_the_only_valid_action(tmp_path, oracle, monkeypatch):
    monkeypatch.setattr(rx, "governance_revalidation", lambda machine_id: lambda: ("BLOCK", "test"))
    case = _case(oracle, "C03")
    held = rx.assess_trial(rx.run_trial(case, "P", oracle, tmp_path / "p"), case)
    blind = rx.assess_trial(rx.run_trial(case, "B0", oracle, tmp_path / "b0"), case)
    assert (held["terminal_actions"], held["oracle_valid"]) == ("HOLD", True)  # R8
    assert (blind["terminal_actions"], blind["oracle_valid"]) == ("REDISPATCH", False)


def test_trials_are_isolated(tmp_path, oracle):
    case = _case(oracle, "C03")
    first = rx.assess_trial(rx.run_trial(case, "B0", oracle, tmp_path / "a"), case)
    second = rx.assess_trial(rx.run_trial(case, "B0", oracle, tmp_path / "b"), case)
    # Wall-clock latency is excluded by definition (protocol §5).
    assert rx.outcome_hash(first) == rx.outcome_hash(second)


def test_end_to_end_run_is_reproducible_and_self_consistent(tmp_path, oracle, monkeypatch):
    created: list[Path] = []

    class RecordingService(rx.MaintenanceEffectService):
        def __init__(self, db_path, **kwargs):
            created.append(Path(db_path))
            super().__init__(db_path, **kwargs)

    monkeypatch.setattr(rx, "MaintenanceEffectService", RecordingService)
    scratch = tmp_path / "scratch"
    out = rx.run_experiment(
        run_id="t", results_root=tmp_path / "results", replays=2, pipeline=True, scratch_root=scratch
    )
    # Every trial database lived under tmp_path (and was removed afterwards).
    assert created and all(scratch in path.parents for path in created)
    assert len(set(created)) == len(created)  # one fresh database per trial
    assert list(scratch.iterdir()) == []

    summary = json.loads((out / "summary.json").read_text())
    assert summary["primary_trials"] == 52
    assert summary["replays_are_independent_samples"] is False
    assert summary["determinism"]["identical_across_replays"] is True
    expected = oracle["metrics"]["denominators_per_policy"]
    for policy, metrics in summary["metrics_per_policy"].items():
        for name, n_cases in expected.items():
            assert metrics[name]["N"] == n_cases, (policy, name)
        assert metrics["unauthorized_effect_rate"]["report_as"] == "not evaluated"

    with (out / "trials.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len([r for r in rows if r["set"] == "primary"]) == 52
    assert len([r for r in rows if r["set"] == "stress"]) == 8
    # Aggregates recompute from the trial-level CSV.
    for policy in rx.POLICY_ORDER:
        dup = sum(r["duplicate_effect"] == "True" for r in rows if r["set"] == "primary" and r["policy"] == policy)
        assert dup == summary["metrics_per_policy"][policy]["duplicate_effect_rate"]["n"]

    manifest = json.loads((out / "manifest.json").read_text())
    for name, digest in manifest["outputs_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    assert manifest["frozen_protocol"]["oracle_sha256"] == hashlib.sha256(
        (rx.PROTOCOL_DIR / "oracle_table.json").read_bytes()
    ).hexdigest()
    assert set(summary["decision_latency_ns_descriptive"]["per_policy"]) == set(rx.POLICY_ORDER)
    for row in summary["pipeline_crosscheck"]["rows"]:
        assert row["single_effect_completion"] == (
            row["graph_outcome"] == "graph_success" and row["committed_effects"] == 1
        )
    assert summary["pipeline_crosscheck"]["executed"] is True
    assert len(summary["pipeline_crosscheck"]["rows"]) == len(rx.CROSSCHECK_CASES) * len(rx.CROSSCHECK_POLICIES)
    assert not any(Path(rx.RESULTS_ROOT).glob("t"))


def test_code_revision_handles_deleted_renamed_and_untracked_paths(monkeypatch, tmp_path):
    (tmp_path / "app" / "newpkg").mkdir(parents=True)
    (tmp_path / "app" / "newpkg" / "mod.py").write_text("x = 1\n")
    (tmp_path / "app" / "kept.py").write_text("y = 2\n")
    outputs = {
        ("rev-parse", "HEAD"): "abc\n",
        ("rev-parse", "--abbrev-ref", "HEAD"): "branch\n",
        ("rev-list", "HEAD"): f"{rx.FROZEN_ANCHOR}\n",
        ("status", "--porcelain=v1"): " D app/gone.py\n?? app/newpkg/\n M app/kept.py\n",
        ("diff", "HEAD"): "",
        ("diff", "--name-only", "--diff-filter=d", "HEAD"): "app/kept.py\n",
        ("ls-files", "--others", "--exclude-standard"): "app/newpkg/mod.py\n",
    }
    monkeypatch.setattr(rx, "_git", lambda *args: outputs[args])
    monkeypatch.setattr(rx, "REPO_ROOT", tmp_path)
    revision = rx.code_revision()
    assert set(revision["uncommitted_code_sha256"]) == {"app/kept.py", "app/newpkg/mod.py"}
