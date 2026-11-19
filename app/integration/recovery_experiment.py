"""Service-level runner and independent assessor for the frozen ElCon-EE 2027 protocol v1.0.

Usage (writes only under research/elcon2027/results/<run_id>/; refuses to
overwrite an existing run directory):

    .venv/bin/python -m app.integration.recovery_experiment [--run-id ID]

Before any trial it verifies protocol/SHA256SUMS and the frozen service hash.
Every trial uses fresh temporary databases (service ledger, recovery journal), a
fresh SimulatedClock and the exact pre-specified fault schedule. Policies get an
Observation and harness-recorded Evidence only. The assessor reads committed
effects from the service ledger database and recomputes the oracle's evidence
predicates from the recorded queries. It never uses a policy's own account.

Evidence label: In-repository, service-level deterministic simulation. The
optional pipeline cross-check runs through the original LangGraph graph and is
written to a separate table.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import dataclasses
import hashlib
import json
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

from app.agents import CapabilityMatchingAgent, GovernanceAgent
from app.integration.maintenance_effect_service import (
    AcknowledgmentLost,
    EffectLedger,
    FaultSpec,
    MaintenanceEffectService,
    SimulatedClock,
)
from app.integration.recovery_journal import RecoveryJournal
from app.integration.recovery_policies import (
    ACK_STATES,
    POLICIES,
    AckState,
    CapabilityContract,
    DispatchState,
    DriveOutcome,
    Observation,
    drive_policy,
)
from app.models.plan import Plan, PlanStep

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_DIR = REPO_ROOT / "research" / "elcon2027" / "protocol"
RESULTS_ROOT = REPO_ROOT / "research" / "elcon2027" / "results"
FROZEN_ANCHOR = "33ea97cc6585caf9ea294317b82f93d813c40d21"
FROZEN_SERVICE = "app/integration/maintenance_effect_service.py"
EVIDENCE_LABEL = "In-repository, service-level deterministic simulation"
PIPELINE_LABEL = "Opt-in LangGraph pipeline integration cross-check (not the 52-trial evaluation)"
REPLAYS = 5
WORKFLOW_ID = "elcon-trial"
STEP_ID = "step-001"
CAPABILITY = "create_maintenance_ticket"
POLICY_ORDER = ("B0", "B1", "B2", "P")
CROSSCHECK_CASES = ("C03", "C04", "C05", "C08b", "C08c", "C09")
CROSSCHECK_POLICIES = ("B0", "B2", "P")

# Protocol v1.0 §3 "Expected decisions (inferred ... NOT results)", transcribed
# for comparison only: terminal actions per resumer and oracle validity.
PROTOCOL_V1_INFERRED: dict[str, dict[str, tuple[str, bool]]] = {
    "C01": {"B0": ("REDISPATCH", True), "B2": ("REDISPATCH", True), "P": ("REDISPATCH", True)},
    "C02": {"B0": ("REDISPATCH", False), "B2": ("REDISPATCH", True), "P": ("REDISPATCH", True)},
    "C03": {"B0": ("REDISPATCH", False), "B2": ("ADOPT", True), "P": ("ADOPT", True)},
    "C04": {"B0": ("REDISPATCH", True), "B2": ("REDISPATCH", True), "P": ("REDISPATCH", True)},
    "C05": {"B0": ("REDISPATCH", False), "B2": ("HOLD", True), "P": ("HOLD", True)},
    "C06": {"B0": ("REDISPATCH", False), "B2": ("HOLD", True), "P": ("HOLD", True)},
    "C07": {"B0": ("REDISPATCH", True), "B2": ("REDISPATCH", True), "P": ("REDISPATCH", True)},
    "C08a": {"B0": ("REDISPATCH", False), "B2": ("ADOPT", True), "P": ("ADOPT", True)},
    "C08b": {"B0": ("REDISPATCH", False), "B2": ("REDISPATCH", False), "P": ("ADOPT", True)},
    "C08c": {"B0": ("REDISPATCH", False), "B2": ("REDISPATCH", False), "P": ("REDISPATCH", True)},
    "C09": {"B0": ("REDISPATCH", False), "B2": ("REDISPATCH", False), "P": ("HOLD", True)},
    "C10": {"B0": ("REDISPATCH", True), "B2": ("REDISPATCH", True), "P": ("REDISPATCH", True)},
    "C11b": {
        "B0": ("REDISPATCH,REDISPATCH", False),
        "B2": ("REDISPATCH,ADOPT", True),
        "P": ("REDISPATCH,ADOPT", True),
    },
}
for _case in PROTOCOL_V1_INFERRED.values():
    _case["B1"] = _case["B0"]  # protocol §3 table: "B0 = B1"


class ProtocolMismatch(RuntimeError):
    """The frozen protocol or service does not match its recorded hashes."""


class HarnessMismatch(RuntimeError):
    """The executed fault schedule did not produce the oracle's observation."""


# --- frozen-protocol verification -----------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_protocol(protocol_dir: Path = PROTOCOL_DIR, repo_root: Path = REPO_ROOT) -> dict:
    """Check SHA256SUMS and the frozen service hash recorded in README.md."""
    manifest = protocol_dir / "SHA256SUMS"
    files = {}
    for line in manifest.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        actual = _sha256(protocol_dir / name)
        if actual != expected:
            raise ProtocolMismatch(f"{name}: expected {expected}, found {actual}")
        files[name] = actual
    recorded = dict(
        (path, digest)
        for digest, path in re.findall(r"^([0-9a-f]{64})\s+(\S+)$", (protocol_dir / "README.md").read_text(), re.M)
    )
    service_hash = _sha256(repo_root / FROZEN_SERVICE)
    if recorded.get(FROZEN_SERVICE) != service_hash:
        raise ProtocolMismatch(f"{FROZEN_SERVICE} differs from the hash recorded at freeze")
    return {
        "protocol_files": files,
        "sha256sums_sha256": _sha256(manifest),
        "oracle_sha256": files["oracle_table.json"],
        "frozen_service_sha256": service_hash,
    }


def load_oracle(protocol_dir: Path = PROTOCOL_DIR) -> dict:
    return json.loads((protocol_dir / "oracle_table.json").read_text())


# --- REVALIDATE: genuine read-only GovernanceAgent re-evaluation ----------


def harness_plan(machine_id: str) -> Plan:
    """The one-step plan used by the harness (disclosed: test-supplied, no Planner)."""
    return Plan(
        goal_id="elcon-maintenance-goal",
        goal_type="maintenance_ticket",
        payload={"machine_id": machine_id, "summary": "Bearing temperature high"},
        steps=[
            PlanStep(
                step_id=STEP_ID,
                title="Create maintenance ticket",
                intent="Open a maintenance work order for the target machine.",
                required_capability=CAPABILITY,
                expected_output="Maintenance ticket identifier.",
            )
        ],
    )


def governance_revalidation(machine_id: str) -> Callable[[], tuple[str, str]]:
    def revalidate() -> tuple[str, str]:
        mapped = CapabilityMatchingAgent().match_plan(harness_plan(machine_id))
        evaluation = GovernanceAgent().evaluate(mapped)
        step = next(s for s in evaluation.steps if s.step_id == STEP_ID)
        return step.decision, "GovernanceAgent re-run (read-only) on the harness one-step plan"

    return revalidate


# --- one service-level trial ----------------------------------------------


def _observation(case: dict, oracle: dict, journal: RecoveryJournal, op_id: str, request: dict) -> Observation:
    attempts = journal.attempts(op_id)
    latest = attempts[-1]
    ack_state = ACK_STATES[latest.reply_status]
    tm = oracle["time_model"]
    return Observation(
        workflow_id=WORKFLOW_ID,
        step_id=STEP_ID,
        operation_id=op_id,
        capability=CAPABILITY,
        adapter="maintenance_effect_service",
        request=dict(request),
        dispatch=DispatchState(len(attempts), latest.dispatched_at),
        ack=AckState(ack_state, latest.reply_status, latest.ticket_id),
        contract=CapabilityContract(**case["declared_contract"]),
        approval={"required": False, "status": "not_required"},
        preconditions={"governance_revalidation": "available", "equipment_state": "not_modelled"},
        resume_at=tm["resume_at"],
        horizon_end=tm["horizon_end"],
    )


def run_trial(case: dict, policy_id: str, oracle: dict, workdir: Path) -> dict:
    """Execute one (case, policy) trial; returns the raw record (no scoring)."""
    harness = case["harness_only"]
    tm = oracle["time_model"]
    machine_id = oracle["operation"]["machine_id"]
    request = {"machine_id": machine_id}
    clock = SimulatedClock(tm["initial_dispatch_at"])
    service = MaintenanceEffectService(
        workdir / "effects.db", deduplicate=harness["service_deduplicate"], clock=clock
    )
    service.schedule_faults([FaultSpec(**f) for f in harness["fault_schedule"]])
    client = service.client()
    journal = RecoveryJournal(workdir / "journal.db")
    op_id = f"{WORKFLOW_ID}:{STEP_ID}"
    journal.record_intent(
        operation_id=op_id,
        workflow_id=WORKFLOW_ID,
        step_id=STEP_ID,
        capability=CAPABILITY,
        adapter="maintenance_effect_service",
        fingerprint="harness",
        now=clock(),
    )

    def dispatch() -> tuple[str | None, str | None]:
        attempt = journal.begin_attempt(op_id, clock())
        try:
            reply = client.submit(op_id, machine_id)
        except AcknowledgmentLost:
            return None, None
        journal.record_reply(attempt, reply.status, reply.ticket_id, clock())
        return reply.status, reply.ticket_id

    dispatch()  # the original dispatch, interrupted per the fault schedule
    clock.advance(tm["resume_at"] - tm["initial_dispatch_at"])
    obs = _observation(case, oracle, journal, op_id, request)  # snapshot shared by resumers
    visible = case["visible_at_resume"]
    if (obs.dispatch.attempts, obs.dispatch.last_dispatch_at, obs.ack.state) != (
        visible["attempts"],
        visible["last_dispatch_at"],
        visible["ack_state"],
    ):
        raise HarnessMismatch(f"{case['id']}: observation differs from oracle visible_at_resume")

    policy = POLICIES[policy_id]
    revalidate = governance_revalidation(machine_id)

    def drive() -> DriveOutcome:
        return drive_policy(
            policy, obs, query=lambda: client.query(op_id), revalidate=revalidate, clock=clock
        )

    def execute(outcome: DriveOutcome) -> dict:
        action = outcome.action
        reply_status = ticket = None
        if action.kind == "REDISPATCH" and outcome.error is None:
            reply_status, ticket = dispatch()
        elif action.kind == "ADOPT":
            ticket = action.ticket_id
        complete = (action.kind == "ADOPT" and ticket is not None) or (
            reply_status in {"committed", "deduplicated"}
        )
        return {
            "steps": [a.kind for a in outcome.steps],
            "terminal": action.kind,
            "basis": action.basis,
            "error": outcome.error,
            "queries": [dataclasses.asdict(q) for q in outcome.evidence.queries],
            "revalidation_provenance": outcome.revalidation_provenance,
            "governance": outcome.evidence.governance,
            "reply_status": reply_status,
            "ticket_id": ticket,
            "complete": complete,
            "simulated_wait_s": outcome.simulated_wait_s,
            "latency_ns": outcome.latency_ns,
        }

    resumers: list[dict] = []
    if harness.get("interleaving", "").startswith("phase-locked"):
        outcomes = [drive() for _ in range(harness["resumers"])]
        resumers = [execute(o) for o in outcomes]
    else:  # single resumer, or sequential duplicate resumes (stale observation)
        for _ in range(harness["resumers"]):
            resumers.append(execute(drive()))

    return {
        "case_id": case["id"],
        "policy": policy_id,
        "observation": {
            "attempts": obs.dispatch.attempts,
            "last_dispatch_at": obs.dispatch.last_dispatch_at,
            "ack_state": obs.ack.state,
            "contract": dataclasses.asdict(obs.contract),
        },
        "resumers": resumers,
        "ledger_db": str(service.db_path),
        "end_clock": clock(),
    }


# --- independent assessment ------------------------------------------------


def _predicates(observation: dict, queries: list[dict]) -> set[str]:
    """Oracle evidence predicates, recomputed from the recorded evidence."""
    contract = observation["contract"]
    true = {"any"}
    if observation["ack_state"] == "failure_received" and observation["attempts"] == 1:
        true.add("failure_response_sole_attempt")
    if contract["deduplicates_by_operation_id"] is True:
        true.add("dedup_contract")
    if queries:
        latest = queries[-1]
        vb, cb = contract["visibility_bound_s"], contract["completion_bound_s"]
        if latest["status"] == "found":
            true.add("query_found")
        elif (
            vb is not None
            and cb is not None
            and latest["query_time"] >= observation["last_dispatch_at"] + cb + vb
        ):
            true.add("query_not_found_authoritative")
    return true


def _ledger_tickets(ledger_db: str, op_id: str) -> list[str]:
    uri = f"{Path(ledger_db).resolve().as_uri()}?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as conn:
        return [r[0] for r in conn.execute(
            "SELECT ticket_id FROM committed_effects WHERE operation_id = ? ORDER BY effect_id",
            (op_id,),
        )]


def assess_trial(raw: dict, case: dict) -> dict:
    """Score a raw trial from the ledger and the oracle; ignores policy self-reports."""
    op_id = f"{WORKFLOW_ID}:{STEP_ID}"
    ledger = EffectLedger(raw["ledger_db"])
    effects = ledger.committed_effect_count(op_id)
    tickets = _ledger_tickets(raw["ledger_db"], op_id)
    dispatches = ledger.dispatch_count(op_id)
    valid_entries = case.get("valid_actions", case.get("per_decision_valid_actions"))
    validity = []
    for resumer in raw["resumers"]:
        if resumer["error"] is not None:
            ok = False  # protocol rule violated by the policy
        elif resumer["governance"] not in (None, "ALLOW"):
            ok = resumer["terminal"] == "HOLD"  # oracle rule R8
        else:
            true = _predicates(raw["observation"], resumer["queries"])
            ok = any(
                e["action"] == resumer["terminal"] and e["evidence"] in true for e in valid_entries
            )
        validity.append(ok)
    all_complete = all(r["complete"] for r in raw["resumers"])
    completed = (
        effects == 1 and all_complete and all(r["ticket_id"] == tickets[0] for r in raw["resumers"])
    )
    # A HOLD produced by a protocol violation is a policy error, not a HOLD.
    holds = sum(r["terminal"] == "HOLD" and r["error"] is None for r in raw["resumers"])
    errors = [r["error"] for r in raw["resumers"] if r["error"]]
    if completed:
        status = "completed"
    elif errors:
        status = "policy_error"
    elif holds:
        status = "held"
    else:
        status = "not_completed"
    elig = case.get("eligibility", {})
    return {
        "case_id": raw["case_id"],
        "set": case["set"],
        "policy": raw["policy"],
        "information_class": case["information_class"],
        "fault_class": case["fault_class"],
        "resumers": len(raw["resumers"]),
        "decision_paths": " | ".join(">".join(r["steps"]) for r in raw["resumers"]),
        "terminal_actions": ",".join(r["terminal"] for r in raw["resumers"]),
        "decision_bases": ",".join(r["basis"] for r in raw["resumers"]),
        "evidence_at_decision": json.dumps([r["queries"] for r in raw["resumers"]]),
        "revalidation_provenance": ";".join(
            sorted({r["revalidation_provenance"] or "none" for r in raw["resumers"]})
        ),
        "policy_errors": ",".join(errors),
        "dispatches": dispatches,
        "recovery_dispatches": dispatches - 1,
        "acks_delivered": ledger.ack_delivered_count(op_id),
        "committed_effects": effects,
        "duplicate_effect": effects > 1,
        "adopted": sum(r["terminal"] == "ADOPT" for r in raw["resumers"]),
        "holds": holds,
        "workflow_status": status,
        "completed": completed,
        "oracle_valid": all(validity),
        "simulated_wait_s": sum(r["simulated_wait_s"] for r in raw["resumers"]),
        "latency_ns": sum(r["latency_ns"] for r in raw["resumers"]),
        "safely_recoverable": elig.get("safely_recoverable"),
        "hindsight_recoverable": elig.get("hindsight_recoverable"),
        "hold_class": elig.get("hold_class"),
        "unnecessary_hold_eligible": elig.get("unnecessary_hold_eligible"),
    }


NON_DETERMINISTIC_FIELDS = {"latency_ns", "replay"}


def outcome_hash(row: Mapping[str, Any]) -> str:
    stable = {k: v for k, v in row.items() if k not in NON_DETERMINISTIC_FIELDS}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


# --- metrics ---------------------------------------------------------------


def _rate(rows: list[dict], numerator: Callable[[dict], bool], eligible: Callable[[dict], bool]) -> dict:
    pool = [r for r in rows if eligible(r)]
    n = sum(1 for r in pool if numerator(r))
    return {"n": n, "N": len(pool), "rate": (n / len(pool)) if pool else None}


METRIC_DEFINITIONS: dict[str, tuple[Callable[[dict], bool], Callable[[dict], bool]]] = {
    "duplicate_effect_rate": (lambda r: r["duplicate_effect"], lambda r: True),
    "correct_recovery_decision_rate": (lambda r: r["oracle_valid"], lambda r: True),
    "recovery_completion_rate": (lambda r: r["completed"], lambda r: r["safely_recoverable"]),
    "hindsight_completion_rate": (lambda r: r["completed"], lambda r: r["hindsight_recoverable"]),
    "unnecessary_hold_rate": (lambda r: r["holds"] > 0, lambda r: r["unnecessary_hold_eligible"]),
    "required_hold_compliance": (
        lambda r: r["holds"] > 0,
        lambda r: r["hold_class"] in {"required", "information_forced"},
    ),
    "information_forced_holds": (
        lambda r: r["holds"] > 0,
        lambda r: r["hold_class"] == "information_forced",
    ),
}


def compute_metrics(primary_rows: list[dict], oracle: dict) -> dict:
    expected = oracle["metrics"]["denominators_per_policy"]
    per_policy = {}
    for policy in POLICY_ORDER:
        rows = [r for r in primary_rows if r["policy"] == policy]
        metrics = {name: _rate(rows, num, elig) for name, (num, elig) in METRIC_DEFINITIONS.items()}
        for name, value in metrics.items():
            if value["N"] != expected[name]:
                raise ProtocolMismatch(f"{policy} {name}: N={value['N']} != frozen {expected[name]}")
        metrics["unauthorized_effect_rate"] = {
            "report_as": "not evaluated",
            "eligible_trials": 0,
            "reason": oracle["metrics"]["unauthorized_effect_rate"]["reason"],
        }
        metrics["dispatches_total"] = sum(r["dispatches"] for r in rows)
        metrics["recovery_dispatches_total"] = sum(r["recovery_dispatches"] for r in rows)
        metrics["committed_effects_total"] = sum(r["committed_effects"] for r in rows)
        metrics["acks_delivered_total"] = sum(r["acks_delivered"] for r in rows)
        metrics["holds_total"] = sum(r["holds"] for r in rows)
        metrics["adopted_total"] = sum(r["adopted"] for r in rows)
        metrics["simulated_wait_s_total"] = sum(r["simulated_wait_s"] for r in rows)
        per_policy[policy] = metrics
    if len(primary_rows) != oracle["metrics"]["primary_trials"]:
        raise ProtocolMismatch(f"primary trials {len(primary_rows)} != frozen 52")
    return per_policy


def compare_with_inferred(primary_rows: list[dict]) -> list[dict]:
    out = []
    for r in primary_rows:
        inferred_actions, inferred_valid = PROTOCOL_V1_INFERRED[r["case_id"]][r["policy"]]
        out.append(
            {
                "case_id": r["case_id"],
                "policy": r["policy"],
                "inferred": f"{inferred_actions} ({'valid' if inferred_valid else 'invalid'})",
                "observed": f"{r['terminal_actions']} ({'valid' if r['oracle_valid'] else 'invalid'})",
                "match": inferred_actions == r["terminal_actions"] and inferred_valid == r["oracle_valid"],
            }
        )
    return out


# --- pipeline cross-check (separate table) --------------------------------


def run_pipeline_trial(case: dict, policy_id: str, oracle: dict, workdir: Path) -> dict:
    """One case through the original LangGraph graph with the opt-in guard."""
    from langgraph.checkpoint.sqlite import SqliteSaver

    import app.agents.execution_agent as execution_agent_module
    from app.adapters import get_adapter
    from app.integration.maintenance_effect_adapter import MaintenanceEffectAdapter
    from app.integration.recovery_guard import RecoveryGuard
    from app.langgraph_runtime.graph import build_graph

    harness = case["harness_only"]
    tm = oracle["time_model"]
    machine_id = oracle["operation"]["machine_id"]
    clock = SimulatedClock(tm["initial_dispatch_at"])
    service = MaintenanceEffectService(
        workdir / "effects.db", deduplicate=harness["service_deduplicate"], clock=clock
    )
    service.schedule_faults([FaultSpec(**f) for f in harness["fault_schedule"]])
    client = service.client()
    journal = RecoveryJournal(workdir / "journal.db")
    guard = RecoveryGuard(
        journal,
        CapabilityContract(**case["declared_contract"]),
        clock,
        policy=POLICIES[policy_id],
        revalidate=governance_revalidation(machine_id),
    )
    adapter = MaintenanceEffectAdapter(client, guard=guard)

    def resolve(name: str):
        return adapter if name == "rest_adapter" else get_adapter(name)

    plan = harness_plan(machine_id)
    initial = {
        "case_id": f"pipeline-{case['id']}-{policy_id}",
        "goal": None,
        "plan": plan.model_dump(),
        "evaluation_governance_plan": None,  # real GovernanceAgent runs in governance_node
        "trace": [],
        "stage_latencies_ms": {},
        "approval_required": False,
        "approval_resumed": False,
        "approval_payload": None,
        "approval_required_step_id": None,
        "approval_state": None,
        "approved_by": None,
        "approval_token": None,
        "resumed_from_interrupt": False,
        "approval_validation_error": None,
        "approval_execution_performed": False,
        "approval_resume_mutation": None,
        "controlled_approval_execution": False,
    }
    thread_id = f"elcon-pipeline-{case['id']}-{policy_id}"
    config = {"configurable": {"thread_id": thread_id}}
    op_id = f"{thread_id}:{STEP_ID}"
    checkpoint_db = str(workdir / "checkpoints.db")
    first = "completed"
    with mock.patch.object(execution_agent_module, "get_adapter", resolve):
        with SqliteSaver.from_conn_string(checkpoint_db) as saver:
            graph = build_graph().compile(checkpointer=saver)
            try:
                graph.invoke(initial, config=config)
            except AcknowledgmentLost:
                first = "AcknowledgmentLost"
        clock.advance(tm["resume_at"] - tm["initial_dispatch_at"])
        with SqliteSaver.from_conn_string(checkpoint_db) as saver:
            graph = build_graph().compile(checkpointer=saver)
            final = graph.invoke(None, config=config)
            snapshot = graph.get_state(config)
    if first != "AcknowledgmentLost":
        raise HarnessMismatch(f"{case['id']}/{policy_id}: first pipeline attempt was not interrupted")
    result = final.get("execution_result")
    interrupts = [i.value for i in final.get("__interrupt__", [])]
    recovery = [d for d in journal.decisions(op_id) if d.action != "DISPATCH"]
    ledger = EffectLedger(service.db_path)
    # graph_outcome is what the LangGraph run reported; it is NOT the protocol's
    # completion definition, which also requires exactly one committed effect.
    if result is not None and result["final_status"] == "success":
        graph_outcome = "graph_success"
    elif interrupts:
        graph_outcome = "interrupted_hold"
    else:
        graph_outcome = "other"
    effects = ledger.committed_effect_count(op_id)
    return {
        "case_id": case["id"],
        "policy": policy_id,
        "first_attempt": first,
        "recovery_decision": ",".join(d.action for d in recovery),
        "recovery_basis": ",".join(d.basis for d in recovery),
        "dispatches": ledger.dispatch_count(op_id),
        "acks_delivered": ledger.ack_delivered_count(op_id),
        "committed_effects": effects,
        "graph_outcome": graph_outcome,
        "single_effect_completion": graph_outcome == "graph_success" and effects == 1,
        "hold_reason": ",".join(i.get("reason", "") for i in interrupts),
        "has_execution_result": result is not None,
        "pending_tasks": ",".join(t.name for t in snapshot.tasks),
    }


# --- run orchestration and outputs ----------------------------------------


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout


def code_revision() -> dict:
    status = _git("status", "--porcelain=v1").splitlines()
    modified = _git("diff", "--name-only", "--diff-filter=d", "HEAD").splitlines()
    untracked = _git("ls-files", "--others", "--exclude-standard").splitlines()
    code = sorted(
        {p for p in modified + untracked if p.startswith(("app/", "tests/")) and p.endswith(".py")}
    )
    return {
        "head": _git("rev-parse", "HEAD").strip(),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "frozen_anchor": FROZEN_ANCHOR,
        "anchor_is_ancestor_or_head": FROZEN_ANCHOR
        in _git("rev-list", "HEAD").split(),
        "git_status_porcelain": status,
        "tracked_diff_sha256": hashlib.sha256(_git("diff", "HEAD").encode()).hexdigest(),
        "uncommitted_code_sha256": {p: _sha256(REPO_ROOT / p) for p in code},
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(
    *,
    run_id: str,
    results_root: Path = RESULTS_ROOT,
    replays: int = REPLAYS,
    pipeline: bool = True,
    protocol_dir: Path = PROTOCOL_DIR,
    command: str = "",
    scratch_root: Path | None = None,
) -> Path:
    out = results_root / run_id
    if out.exists():
        raise FileExistsError(f"{out} exists; refusing to overwrite a previous run")
    frozen = verify_frozen_protocol(protocol_dir)
    oracle = load_oracle(protocol_dir)
    revision = code_revision()
    cases = {c["id"]: c for c in oracle["cases"] + oracle["stress_cases"]}
    order = [c["id"] for c in oracle["cases"]] + [c["id"] for c in oracle["stress_cases"]]

    raw_records, rows = [], []
    if scratch_root is not None:
        scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="elcon-run-", dir=scratch_root) as scratch:
        for replay in range(replays):
            for case_id in order:
                for policy in POLICY_ORDER:
                    workdir = Path(scratch) / f"r{replay}" / case_id / policy
                    raw = run_trial(cases[case_id], policy, oracle, workdir)
                    row = {"replay": replay, **assess_trial(raw, cases[case_id])}
                    raw_records.append({"replay": replay, **{k: v for k, v in raw.items() if k != "ledger_db"}})
                    rows.append(row)

        hashes: dict[tuple[str, str], set[str]] = {}
        for r in rows:
            hashes.setdefault((r["case_id"], r["policy"]), set()).add(outcome_hash(r))
        nondeterministic = sorted(f"{c}/{p}" for (c, p), h in hashes.items() if len(h) != 1)

        first = [r for r in rows if r["replay"] == 0]
        primary = [r for r in first if r["set"] == "primary"]
        stress = [r for r in first if r["set"] == "stress"]
        metrics = compute_metrics(primary, oracle)
        latency = {}
        for policy in POLICY_ORDER:
            values = [r["latency_ns"] for r in rows if r["set"] == "primary" and r["policy"] == policy]
            latency[policy] = {
                "median_ns": statistics.median(values),
                "max_ns": max(values),
                "executions": len(values),
            }
        inferred = compare_with_inferred(primary)

        crosscheck = []
        if pipeline:
            service_level = {(r["case_id"], r["policy"]): r for r in primary}
            for case_id in CROSSCHECK_CASES:
                for policy in CROSSCHECK_POLICIES:
                    workdir = Path(scratch) / "pipeline" / case_id / policy
                    pr = run_pipeline_trial(cases[case_id], policy, oracle, workdir)
                    sl = service_level[(case_id, policy)]
                    pr["service_level_terminal"] = sl["terminal_actions"]
                    pr["service_level_effects"] = sl["committed_effects"]
                    pr["matches_service_level"] = (
                        pr["recovery_decision"] == sl["terminal_actions"]
                        and pr["committed_effects"] == sl["committed_effects"]
                    )
                    crosscheck.append(pr)

    out.mkdir(parents=True)
    _write_csv(out / "trials.csv", first)
    (out / "raw_trials.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in raw_records)
    )
    if crosscheck:
        _write_csv(out / "pipeline_crosscheck.csv", crosscheck)
    summary = {
        "evidence_label": EVIDENCE_LABEL,
        "protocol_version": oracle["protocol_version"],
        "primary_trials": len(primary),
        "replays_per_trial": replays,
        "executions_total": len(rows),
        "replays_are_independent_samples": False,
        "determinism": {
            "identical_across_replays": not nondeterministic,
            "nondeterministic_trials": nondeterministic,
            "excluded_fields": sorted(NON_DETERMINISTIC_FIELDS),
        },
        "denominators_verified_against": "oracle_table.json metrics.denominators_per_policy",
        "metrics_per_policy": metrics,
        "decision_latency_ns_descriptive": {
            "scope": "wall-clock inside policy calls, summed per trial; all primary executions "
            "incl. replays; excludes harness I/O and simulated waits; descriptive only",
            "per_policy": latency,
        },
        "comparison_with_protocol_v1_inferred": {
            "matches": sum(i["match"] for i in inferred),
            "total": len(inferred),
            "mismatches": [i for i in inferred if not i["match"]],
        },
        "stress_cases": {
            "label": "Concurrency stress (C11a, C12): excluded from primary metrics",
            "rows": [
                {k: r[k] for k in ("case_id", "policy", "terminal_actions", "oracle_valid",
                                   "dispatches", "committed_effects", "workflow_status")}
                for r in stress
            ],
        },
        "pipeline_crosscheck": {
            "label": PIPELINE_LABEL,
            "executed": bool(crosscheck),
            "rows": crosscheck,
            "all_match_service_level": all(c["matches_service_level"] for c in crosscheck)
            if crosscheck
            else None,
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (out / "REPORT.md").write_text(render_report(run_id, summary, primary, inferred, crosscheck))
    manifest = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "evidence_label": EVIDENCE_LABEL,
        "frozen_protocol": frozen,
        "code_revision": revision,
        "configuration": {
            "replays": replays,
            "policies": list(POLICY_ORDER),
            "primary_cases": [c["id"] for c in oracle["cases"]],
            "stress_cases": [c["id"] for c in oracle["stress_cases"]],
            "pipeline_crosscheck": {
                "cases": list(CROSSCHECK_CASES) if pipeline else [],
                "policies": list(CROSSCHECK_POLICIES) if pipeline else [],
            },
            "revalidation": "GovernanceAgent re-run (read-only) on the harness one-step plan",
            "time_model": oracle["time_model"],
        },
        "environment": {
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
        },
        "outputs_sha256": {
            p.name: _sha256(p) for p in sorted(out.iterdir()) if p.name != "manifest.json"
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return out


def _fmt(metric: dict) -> str:
    return f"{metric['n']}/{metric['N']}"


def render_report(run_id: str, summary: dict, primary: list[dict], inferred: list[dict], crosscheck: list[dict]) -> str:
    m = summary["metrics_per_policy"]
    lines = [
        f"# ElCon-EE 2027 recovery study — run `{run_id}`",
        "",
        f"**Evidence label:** {summary['evidence_label']}. Protocol v{summary['protocol_version']} (frozen).",
        f"Primary: {summary['primary_trials']} case-policy trials; {summary['replays_per_trial']} deterministic "
        f"replays each ({summary['executions_total']} executions incl. stress), used only as a reproducibility check, "
        f"not as samples. Identical across replays: {summary['determinism']['identical_across_replays']}.",
        "",
        "## Primary metrics (n/N per policy; generated from trials.csv)",
        "",
        "| Metric | " + " | ".join(POLICY_ORDER) + " |",
        "|---|" + "---|" * len(POLICY_ORDER),
    ]
    for name in METRIC_DEFINITIONS:
        lines.append(f"| {name} | " + " | ".join(_fmt(m[p][name]) for p in POLICY_ORDER) + " |")
    for name in ("dispatches_total", "recovery_dispatches_total", "acks_delivered_total",
                 "committed_effects_total", "adopted_total", "holds_total", "simulated_wait_s_total"):
        lines.append(f"| {name} | " + " | ".join(str(m[p][name]) for p in POLICY_ORDER) + " |")
    lat = summary["decision_latency_ns_descriptive"]["per_policy"]
    lines += [
        "| unauthorized_effect_rate | " + " | ".join("not evaluated" for _ in POLICY_ORDER) + " |",
        "| decision latency median / max (ns, wall clock, descriptive) | "
        + " | ".join(f"{lat[p]['median_ns']:.0f} / {lat[p]['max_ns']}" for p in POLICY_ORDER) + " |",
        "",
        "## Case-by-case (replay 0): terminal actions / oracle validity / committed effects / status",
        "",
        "| Case | " + " | ".join(POLICY_ORDER) + " |",
        "|---|" + "---|" * len(POLICY_ORDER),
    ]
    by = {(r["case_id"], r["policy"]): r for r in primary}
    for case_id in dict.fromkeys(r["case_id"] for r in primary):
        cells = []
        for p in POLICY_ORDER:
            r = by[(case_id, p)]
            cells.append(
                f"{r['terminal_actions']} {'✓' if r['oracle_valid'] else '✗'} e={r['committed_effects']} {r['workflow_status']}"
            )
        lines.append(f"| {case_id} | " + " | ".join(cells) + " |")
    cmp = summary["comparison_with_protocol_v1_inferred"]
    lines += [
        "",
        f"## Comparison with protocol v1.0 §3 inferred behaviour: {cmp['matches']}/{cmp['total']} match",
        "",
    ]
    for mis in cmp["mismatches"]:
        lines.append(f"- MISMATCH {mis['case_id']}/{mis['policy']}: inferred {mis['inferred']}, observed {mis['observed']}")
    lines += ["", "## Concurrency stress cases (excluded from primary metrics)", "",
              "| Case | Policy | Terminal | Valid | Dispatches | Effects | Status |", "|---|---|---|---|---|---|---|"]
    for r in summary["stress_cases"]["rows"]:
        lines.append(
            f"| {r['case_id']} | {r['policy']} | {r['terminal_actions']} | {r['oracle_valid']} | "
            f"{r['dispatches']} | {r['committed_effects']} | {r['workflow_status']} |"
        )
    if crosscheck:
        lines += ["", f"## {PIPELINE_LABEL}", "",
                  "Graph outcome = what the LangGraph run reported. Single-effect completion additionally "
                  "requires exactly one committed effect in the ledger.", "",
                  "| Case | Policy | Recovery decision | Dispatches | Effects | Graph outcome | "
                  "Single-effect completion | Service-level terminal / effects | Match |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for c in crosscheck:
            lines.append(
                f"| {c['case_id']} | {c['policy']} | {c['recovery_decision']} | {c['dispatches']} | "
                f"{c['committed_effects']} | {c['graph_outcome']} | {c['single_effect_completion']} | "
                f"{c['service_level_terminal']} / {c['service_level_effects']} | {c['matches_service_level']} |"
            )
    lines += [
        "",
        "Not claimed: exactly-once execution, late or in-flight commits (F5c), concurrent-resume safety, "
        "pipeline-integrated or industrial evidence for the primary matrix, or a new waiting algorithm.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--no-pipeline-crosscheck", action="store_true")
    args = parser.parse_args(argv)
    head = _git("rev-parse", "--short", "HEAD").strip()
    run_id = args.run_id or datetime.now(timezone.utc).strftime(f"%Y%m%dT%H%M%SZ-{head}")
    command = " ".join([".venv/bin/python -m app.integration.recovery_experiment", *(argv or sys.argv[1:])])
    out = run_experiment(run_id=run_id, pipeline=not args.no_pipeline_crosscheck, command=command)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
