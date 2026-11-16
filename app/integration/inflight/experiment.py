"""Extension v1 formal-run driver.

    .venv/bin/python -m app.integration.inflight.experiment --run-id <id> \
        --results-root research/elcon2027/extension_v1/results --scratch-root <tmp dir>

Refuses to run unless every file listed in protocol/FREEZE_MANIFEST.txt still has its frozen
SHA-256. Writes (never overwrites) <results-root>/<run-id>/:
  raw_executions.jsonl, executions.csv          RQ1/RQ2 (sets: compliant, violation, governance)
  raw_replay.jsonl, replay.csv                  RQ3 (two-step LangGraph replay)
  regression_original_cases.csv                 regression check (labelled; not original evidence)
  summary.json, manifest.json
Per-execution databases go to the scratch root (fresh per execution).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXT = REPO / "research/elcon2027/extension_v1"
PROTOCOL = EXT / "protocol"
FREEZE = PROTOCOL / "FREEZE_MANIFEST.txt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze() -> dict[str, str]:
    entries = {}
    for line in FREEZE.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        entries[rel] = digest
    bad = [rel for rel, d in entries.items() if sha256(REPO / rel) != d]
    if bad:
        raise SystemExit(f"frozen files changed, refusing to run: {bad}")
    return entries


def _csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _flat(r: dict) -> dict:
    a = r["assessment"]
    return {
        "case_id": r["case_id"], "set": r["set"], "policy": r["policy"], "replay": r["replay"],
        "decision_path": r["decision_path"], "decision_basis": r["decision_basis"],
        "decision_time": r["decision_time"], "final": r["final"], "recorded_ticket": r["recorded_ticket"],
        "simulated_wait_s": r["simulated_wait_s"], "policy_error": r["policy_error"],
        "governance": ",".join(v["decision"] for v in r["revalidations"]),
        **{k: a[k] for k in ("effects_at_decision", "eventual_effects", "duplicate_eventual", "late_duplicate",
                             "censored", "eventual_status", "workflow_outcome", "completed_single_effect",
                             "missing_effect", "adoption_consistent", "dispatches", "queries",
                             "dispatches_while_invalid", "effects_while_invalid", "commits_after_hold")},
    }


def _signature(row: dict) -> str:
    keep = {k: v for k, v in row.items() if k not in ("replay", "recorded_ticket")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()


def summarize(rows: list[dict]) -> dict:
    out: dict = {}
    for set_name in ("compliant", "violation", "governance"):
        per: dict = {}
        for pol in sorted({r["policy"] for r in rows}):
            rs = [r for r in rows if r["set"] == set_name and r["policy"] == pol and r["replay"] == 0]
            if not rs:
                continue
            unc = [r for r in rs if not r["censored"]]
            per[pol] = {
                "executions": len(rs),
                "censored": len(rs) - len(unc),
                "duplicate_eventual": {"n": sum(r["duplicate_eventual"] for r in unc), "N": len(unc)},
                "late_duplicate": {"n": sum(r["late_duplicate"] for r in unc), "N": len(unc)},
                "completed_single_effect": {"n": sum(r["completed_single_effect"] for r in rs), "N": len(rs)},
                "held": sum(r["workflow_outcome"] == "held" for r in rs),
                "missing_effect": sum(r["missing_effect"] for r in rs),
                "dispatches": sum(r["dispatches"] for r in rs),
                "queries": sum(r["queries"] for r in rs),
                "simulated_wait_s": sum(r["simulated_wait_s"] for r in rs),
                "dispatches_while_invalid": sum(r["dispatches_while_invalid"] for r in rs),
                "effects_while_invalid": sum(r["effects_while_invalid"] for r in rs),
                "commits_after_hold": sum(r["commits_after_hold"] for r in rs),
                "adopted": sum(r["final"] == "ADOPT" for r in rs),
                "policy_errors": sum(bool(r["policy_error"]) for r in rs),
            }
        out[set_name] = per
    return out


def regression_original_cases(scratch: Path) -> list[dict]:
    """Original single-resumer primary cases on the extension simulator (Δ = 0 mapping)."""
    from app.integration.inflight.runner import run_ext_trial

    oracle = json.loads((REPO / "research/elcon2027/protocol/oracle_table.json").read_text())
    orig_csv = REPO / "research/elcon2027/results/20261110T132939Z-fb77698/trials.csv"
    orig = {(r["case_id"], r["policy"]): r for r in csv.DictReader(orig_csv.open())}
    rows = []
    for c in oracle["cases"]:
        if c["set"] != "primary" or c["harness_only"]["resumers"] != 1:
            continue
        f = c["harness_only"]["fault_schedule"][0]
        if not f["commit"] and f.get("ack_delivered"):
            continue  # C01: delivered failure reply without commit is not representable (see report)
        fault = ({"commit_after": 0.0, "visibility_after": float(f.get("visibility_delay") or 0.0),
                  "ack_delivered": False, "abort_after": None} if f["commit"] else
                 {"commit_after": None, "visibility_after": 0.0, "ack_delivered": False, "abort_after": 0.0})
        case = {"id": c["id"], "set": "regression", "rq": "regression", "declared_contract": c["declared_contract"],
                "provider": {"deduplicate": c["harness_only"]["service_deduplicate"], "auth_check": "none"},
                "first_dispatch_fault": fault,
                "times": {"dispatch_at": 1000.0, "resume_at": 1010.0, "horizon_s": 60.0, "assessment_until": 1600.0},
                "authorization": {"invalid_from": None}}
        for pol in ("B0", "B1", "B2", "P"):
            r = run_ext_trial(case, pol, scratch / f"reg-{c['id']}-{pol}")
            o = orig[(c["id"], pol)]
            rows.append({"case_id": c["id"], "policy": pol,
                         "extension_decision_path": r["decision_path"], "original_decision_path": o["decision_paths"],
                         "extension_effects": r["assessment"]["eventual_effects"],
                         "original_effects": int(o["committed_effects"]),
                         "match": r["decision_path"] == o["decision_paths"]
                         and r["assessment"]["eventual_effects"] == int(o["committed_effects"])})
    return rows


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--results-root", required=True, type=Path)
    ap.add_argument("--scratch-root", required=True, type=Path)
    args = ap.parse_args(argv)
    frozen = verify_freeze()
    out = args.results_root / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    scratch = args.scratch_root / args.run_id
    from app.integration.inflight.pipeline_replay import run_replay_trial
    from app.integration.inflight.runner import run_ext_trial

    doc = json.loads((PROTOCOL / "cases.json").read_text())
    prov = {"protocol_version": doc["extension_protocol_version"],
            "freeze_manifest_sha256": sha256(FREEZE), "cases_json_sha256": sha256(PROTOCOL / "cases.json")}
    started = datetime.now(timezone.utc).isoformat()
    raw, rows = [], []
    for case in doc["cases"]:
        for pol in doc["policies"]:
            for rep in range(doc["replays"]):
                try:
                    r = run_ext_trial(case, pol, scratch / f"{case['id']}-{pol}-r{rep}", replay=rep, provenance=prov)
                except Exception as exc:  # recorded, never dropped
                    r = {"case_id": case["id"], "policy": pol, "replay": rep, "error": repr(exc)}
                    raw.append(r)
                    continue
                raw.append(r)
                rows.append(_flat(r))
    with (out / "raw_executions.jsonl").open("w") as f:
        for r in raw:
            f.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    _csv(out / "executions.csv", rows)
    rraw, rrows = [], []
    for case in doc["replay_cases"]:
        for mode in doc["replay_modes"]:
            for rep in range(doc["replays"]):
                r = run_replay_trial(case, mode, scratch / f"{case['id']}-{mode}-r{rep}", replay=rep, provenance=prov)
                rraw.append(r)
                for sid, s in r["steps"].items():
                    a = s["assessment"]
                    rrows.append({"case_id": r["case_id"], "mode": mode, "replay": rep, "step": sid,
                                  "first_invocation": r["first_invocation"], "graph_outcome": r["graph_outcome"],
                                  "guard_decisions": ";".join(f"{x}/{y}" for x, y in s["guard_recovery_decisions"]),
                                  "eventual_effects": a["eventual_effects"], "duplicate_eventual": a["duplicate_eventual"],
                                  "late_duplicate": a["late_duplicate"], "completed_single_effect": a["completed_single_effect"],
                                  "operation_id": s["operation_id"],
                                  "operation_ids_stable": r["operation_ids_before_resume"] == r["operation_ids_after_resume"]})
    with (out / "raw_replay.jsonl").open("w") as f:
        for r in rraw:
            f.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    _csv(out / "replay.csv", rrows)
    reg = regression_original_cases(scratch / "regression")
    _csv(out / "regression_original_cases.csv", reg)
    groups: dict = defaultdict(set)
    for row in rows:
        groups[(row["case_id"], row["policy"])].add(_signature(row))
    rgroups: dict = defaultdict(set)
    for row in rrows:
        rgroups[(row["case_id"], row["mode"], row["step"])].add(
            json.dumps({k: v for k, v in row.items() if k not in ("replay", "operation_id")}, sort_keys=True))
    summary = {
        "label": "ElCon-EE 2027 extension x1.0 (separate from the original frozen study)",
        "executions": {"service_level": len(raw), "errors": sum("error" in r for r in raw),
                       "replay_runs": len(rraw)},
        "determinism": {"service_level_identical_across_replays": all(len(v) == 1 for v in groups.values()),
                        "replay_identical_across_replays": all(len(v) == 1 for v in rgroups.values())},
        "by_set": summarize(rows),
        "regression_original_cases": {"compared": len(reg), "matches": sum(r["match"] for r in reg)},
        "replays_are_independent_samples": False,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    manifest = {
        "run_id": args.run_id, "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git("rev-parse", "HEAD"), "git_status_short": git("status", "--short").splitlines(),
        "frozen_files": frozen, "provenance": prov,
        "python": sys.version.split()[0], "platform": platform.platform(),
        "outputs": {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps(summary["executions"]), json.dumps(summary["determinism"]),
          json.dumps(summary["regression_original_cases"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
