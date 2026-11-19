"""Independent verification of an extension x1.0 run (stdlib only; imports nothing from app/).

    python3 verify_extension.py <run_dir> <protocol_dir>

1. Every raw execution has the required fields, fresh-database provenance and no error.
2. The assessment is recomputed from the raw event log and ledger with code written separately
   from app/integration/inflight/assessor.py, and compared field by field.
3. summary.json is recomputed from the raw records.
4. Determinism: replays 0-4 of each case x policy agree on all outcome fields.
5. Expected properties of protocol §7 are checked as stated before the run; failures are
   reported, not hidden.
6. Output hashes in manifest.json match the files.
Exit 0 only if checks 1-4 and 6 pass; §7 results are reported either way.
"""

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

run, proto = Path(sys.argv[1]), Path(sys.argv[2])
fails = 0


def check(ok, msg, detail=""):
    global fails
    fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + msg + (f" | {detail}" if detail else ""))


def expect(ok, msg, detail=""):
    print(("HOLDS    " if ok else "VIOLATED ") + msg + (f" | {detail}" if detail else ""))
    return ok


raw = [json.loads(line) for line in (run / "raw_executions.jsonl").read_text().splitlines() if line.strip()]
replay = [json.loads(line) for line in (run / "raw_replay.jsonl").read_text().splitlines() if line.strip()]
summary = json.loads((run / "summary.json").read_text())
manifest = json.loads((run / "manifest.json").read_text())
doc = json.loads((proto / "cases.json").read_text())
cases = {c["id"]: c for c in doc["cases"]}

# 6. output hashes
for name, digest in manifest["outputs"].items():
    check(hashlib.sha256((run / name).read_bytes()).hexdigest() == digest, f"manifest hash {name}")

# 1. completeness
check(len(raw) == len(doc["cases"]) * len(doc["policies"]) * doc["replays"], "service-level executions = 24 x 6 x 5",
      str(len(raw)))
check(not any("error" in r for r in raw), "no execution errors")
need = {"case_id", "policy", "replay", "provenance", "declared_contract", "first_dispatch_fault", "times", "events",
        "effects", "decision_path", "decision_time", "revalidations", "final", "assessment", "pending_at_horizon"}
check(all(need <= set(r) for r in raw), "required per-execution fields present")
check(all(r["provenance"].get("freeze_manifest_sha256") for r in raw), "every execution carries the freeze-manifest hash")


# 2. independent re-assessment
def reassess(r):
    op = next(e["operation_id"] for e in r["events"] if e["kind"] == "submit")
    eff = sorted((e for e in r["effects"] if e["operation_id"] == op), key=lambda e: e["committed_at"])
    inv = r["authorization"].get("invalid_from")
    bad = (lambda t: inv is not None and t >= inv)
    cens = op in r["pending_at_horizon"]
    done = r["final"] in ("ADOPT", "REDISPATCH") and r["recorded_ticket"] is not None
    tick = {e["ticket_id"] for e in eff}
    return {
        "eventual_effects": len(eff),
        "effects_at_decision": len([e for e in eff if e["committed_at"] <= r["decision_time"]]),
        "duplicate_eventual": len(eff) >= 2,
        "late_duplicate": len(eff) >= 2 and len([e for e in eff if e["committed_at"] <= r["decision_time"]]) < 2,
        "censored": cens,
        "completed_single_effect": done and len(eff) == 1 and not cens and r["recorded_ticket"] in tick,
        "missing_effect": done and not eff,
        "dispatches": len([e for e in r["events"] if e["kind"] == "submit"]),
        "dispatches_while_invalid": len([e for e in r["events"] if e["kind"] == "submit" and bad(e["time"])]),
        "effects_while_invalid": len([e for e in eff if bad(e["committed_at"])]),
        "commits_after_hold": len([e for e in eff if r["final"] == "HOLD" and e["committed_at"] > r["decision_time"]]),
    }


mismatch = [(r["case_id"], r["policy"], r["replay"], k) for r in raw for k, v in reassess(r).items() if r["assessment"][k] != v]
check(not mismatch, "independent re-assessment equals recorded assessment (11 fields x 720)", str(mismatch[:5]))

# 3. summary recomputation (replay 0)
ok = True
for s, per in summary["by_set"].items():
    for pol, m in per.items():
        rs = [r for r in raw if r["set"] == s and r["policy"] == pol and r["replay"] == 0]
        unc = [r for r in rs if not reassess(r)["censored"]]
        ok &= m["duplicate_eventual"] == {"n": sum(reassess(r)["duplicate_eventual"] for r in unc), "N": len(unc)}
        ok &= m["completed_single_effect"]["n"] == sum(reassess(r)["completed_single_effect"] for r in rs)
        ok &= m["simulated_wait_s"] == sum(r["simulated_wait_s"] for r in rs)
        ok &= m["dispatches_while_invalid"] == sum(reassess(r)["dispatches_while_invalid"] for r in rs)
        ok &= m["commits_after_hold"] == sum(reassess(r)["commits_after_hold"] for r in rs)
check(ok, "summary.json recomputed from raw records")

# 4. determinism
groups = defaultdict(set)
for r in raw:
    groups[(r["case_id"], r["policy"])].add(json.dumps([r["decision_path"], r["final"], r["simulated_wait_s"],
                                                        [(e["committed_at"], e["visible_at"]) for e in r["effects"]],
                                                        reassess(r)], sort_keys=True))
check(all(len(v) == 1 for v in groups.values()), "deterministic across 5 replays (service level)")
rg = defaultdict(set)
for r in replay:
    rg[(r["case_id"], r["mode"])].add(json.dumps([[(e["operation_id"].split(":")[1], e["committed_at"]) for e in r["effects"]],
                                                  r["graph_outcome"]], sort_keys=True))
check(all(len(v) == 1 for v in rg.values()) and len(replay) == 4 * 5 * 5, "replay runs: 100, deterministic")
reg = list(csv.DictReader((run / "regression_original_cases.csv").open()))
check(len(reg) == 44 and all(r["match"] == "True" for r in reg), "regression: 44/44 original cases reproduced")

# 5. expected properties (protocol §7), replay 0
R = {(r["case_id"], r["policy"]): r for r in raw if r["replay"] == 0}
A = {k: reassess(v) for k, v in R.items()}
print("\n# Protocol §7 expected properties")
expect(all(A[(c, "B2")]["duplicate_eventual"] for c in ["E02", "E03", "E05", "E06", "E08", "E11", "E13"]),
       "1a B2 duplicates in E02, E03, E05, E06, E08, E11, E13")
expect(all(A[(c, "B2")]["late_duplicate"] for c in ["E02", "E03", "E05", "E06", "E11", "E13"]),
       "1b ...as late duplicates in E02-E06 (excl. E04), E11, E13")
comp = [c for c in cases if cases[c]["set"] == "compliant"]
expect(all(not A[(c, p)]["duplicate_eventual"] for c in comp for p in ("P", "R_LI")), "2a P and R_LI: no duplicate in E01-E16")
expect(all(R[(c, p)]["final"] == "HOLD" for c in ["E11", "E12", "E13", "E16"] for p in ("P", "R_LI")),
       "2b P and R_LI hold in E11, E12, E13, E16")
expect(all(A[(c, p)]["commits_after_hold"] == 1 for c in ["E11", "E13"] for p in ("P", "R_LI")),
       "2c pending request commits after the hold in E11, E13")
expect(all(A[(c, p)]["eventual_effects"] == 1 for c in ["E14", "E15"] for p in doc["policies"]), "3 E14/E15: one effect for every policy")
expect(all(A[(c, p)]["duplicate_eventual"] for c in ["V01", "V02"] for p in ("P", "R_LI")), "4 P and R_LI duplicate under violated contracts V01, V02")
G = [c for c in cases if cases[c]["set"] == "governance"]
expect(all(R[(c, p)]["final"] == "HOLD" for c in G for p in ("B1", "B2", "P", "R_LI")), "5a B1/B2/P/R_LI hold in every G case")
expect(all(A[(c, "B0")]["dispatches_while_invalid"] == 1 for c in G), "5b B0 dispatches while invalid in every G case")
expect([c for c in G if R[(c, "P_A")]["final"] == "ADOPT"] == ["G01", "G06"], "5c P_A adopts exactly in G01, G06",
       str([c for c in G if R[(c, "P_A")]["final"] == "ADOPT"]))
expect(all(A[(c, "P")]["commits_after_hold"] == 1 for c in ["G02", "G04"]) and A[("G03", "P")]["eventual_effects"] == 0,
       "5d pending request commits after P's hold in G02, G04; aborted under commit-time check in G03")
by = {(r["case_id"], r["mode"]): r for r in replay if r["replay"] == 0}
expect(by[("R01", "UNPROTECTED")]["steps"]["s1"]["assessment"]["eventual_effects"] == 2
       and by[("R03", "UNPROTECTED")]["steps"]["s1"]["assessment"]["eventual_effects"] == 2,
       "6a unprotected replay repeats completed step s1 without deduplication")
expect(all(by[(c, m)]["steps"]["s1"]["guard_recovery_decisions"] == [["ADOPT", "acknowledged_reply"]]
           for c in ("R01", "R02", "R03", "R04") for m in ("B0", "B2", "P", "R_LI")), "6b guard adopts s1 in every guarded run")
expect(all(r["operation_ids_before_resume"] == r["operation_ids_after_resume"] for r in replay)
       and all(len({s["operation_id"] for s in r["steps"].values()}) == 2 for r in replay),
       "6c operation IDs stable across resume and distinct per step")
print(f"\n{'ALL CHECKS PASSED' if fails == 0 else f'{fails} CHECK(S) FAILED'}")
sys.exit(1 if fails else 0)
