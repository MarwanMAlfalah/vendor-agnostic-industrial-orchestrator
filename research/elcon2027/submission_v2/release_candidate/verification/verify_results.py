"""Independent verification of the ElCon-EE 2027 frozen-protocol results (stdlib only).

Recomputes every reported number from the raw records and the frozen oracle WITHOUT importing
the experiment runner or its assessor:

    python3 verify_results.py --run <run_dir> --oracle <oracle_table.json>

Checks:
  * record counts: 300 raw executions = 60 case-policy combinations x 5 replays
    (52 primary + 8 stress); identical decisions across replays;
  * observations and contracts equal the oracle's `visible_at_resume` / `declared_contract`;
  * oracle validity recomputed from the recorded queries and the oracle evidence predicates;
  * committed effects and dispatches recomputed from the fault schedule plus recorded replies
    (independent of the ledger) and compared with the ledger-based counts in trials.csv;
  * all primary metrics with denominators taken from the oracle eligibility flags;
  * dispatch, effect and simulated-wait totals; agreement with summary.json;
  * pipeline cross-check: 18 rows, all matching service level, and the rows that report
    graph success while the ledger holds two effects.
Exit status 0 only if every check passes.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict

POLICIES = ("B0", "B1", "B2", "P")


def predicates(obs, queries):
    c = obs["contract"]
    p = {"any"}
    if obs["ack_state"] == "failure_received" and obs["attempts"] == 1:
        p.add("failure_response_sole_attempt")
    if c["deduplicates_by_operation_id"] is True:
        p.add("dedup_contract")
    if queries:
        q = queries[-1]
        vb, cb = c["visibility_bound_s"], c["completion_bound_s"]
        if q["status"] == "found":
            p.add("query_found")
        elif vb is not None and cb is not None and q["query_time"] >= obs["last_dispatch_at"] + cb + vb:
            p.add("query_not_found_authoritative")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--oracle", required=True)
    a = ap.parse_args()
    problems = []

    def check(cond, msg):
        if not cond:
            problems.append(msg)

    oracle = json.load(open(a.oracle))
    cases = {c["id"]: c for c in oracle["cases"] + oracle["stress_cases"]}
    raw = [json.loads(line) for line in open(f"{a.run}/raw_trials.jsonl")]
    rows = list(csv.DictReader(open(f"{a.run}/trials.csv")))
    csv_by = {(r["case_id"], r["policy"]): r for r in rows}
    summary = json.load(open(f"{a.run}/summary.json"))
    pipe = list(csv.DictReader(open(f"{a.run}/pipeline_crosscheck.csv")))

    by = defaultdict(list)
    for r in raw:
        by[(r["case_id"], r["policy"])].append(r)
    check(len(raw) == 300, f"raw records {len(raw)} != 300")
    check(len(by) == 60, f"combinations {len(by)} != 60")
    check(all(len(v) == 5 for v in by.values()), "not exactly 5 replays per combination")
    n_primary = sum(1 for k in by if cases[k[0]]["set"] == "primary")
    check(n_primary == 52, f"primary combinations {n_primary} != 52")
    check(len(by) - n_primary == 8, "stress combinations != 8")
    check(len(rows) == 60, f"trials.csv rows {len(rows)} != 60")

    res = {}
    for key, reps in by.items():
        case = cases[key[0]]
        sig = {json.dumps([(x["terminal"], x["basis"], x["queries"], x["reply_status"]) for x in r["resumers"]],
                          sort_keys=True) for r in reps}
        check(len(sig) == 1, f"{key}: replays differ")
        r = reps[0]
        vis = case["visible_at_resume"]
        obs = r["observation"]
        check((obs["attempts"], obs["last_dispatch_at"], obs["ack_state"]) ==
              (vis["attempts"], vis["last_dispatch_at"], vis["ack_state"]), f"{key}: observation != oracle")
        check(obs["contract"] == case["declared_contract"], f"{key}: contract != oracle")
        entries = case.get("valid_actions", case.get("per_decision_valid_actions"))
        valid = all(x["error"] is None and any(e["action"] == x["terminal"] and e["evidence"] in predicates(obs, x["queries"])
                                               for e in entries) for x in r["resumers"])
        effects = int(case["harness_only"]["fault_schedule"][0]["commit"])
        effects += sum(1 for x in r["resumers"] if x["terminal"] == "REDISPATCH" and x["reply_status"] == "committed")
        dispatches = 1 + sum(1 for x in r["resumers"] if x["terminal"] == "REDISPATCH")
        complete = (effects == 1 and all(x["complete"] for x in r["resumers"])
                    and len({x["ticket_id"] for x in r["resumers"]}) == 1)
        holds = sum(1 for x in r["resumers"] if x["terminal"] == "HOLD" and x["error"] is None)
        adopted = sum(1 for x in r["resumers"] if x["terminal"] == "ADOPT")
        wait = sum(x["simulated_wait_s"] for x in r["resumers"])
        row = csv_by[key]
        for name, mine, theirs in [("oracle_valid", valid, row["oracle_valid"] == "True"),
                                   ("committed_effects", effects, int(row["committed_effects"])),
                                   ("dispatches", dispatches, int(row["dispatches"])),
                                   ("completed", complete, row["completed"] == "True"),
                                   ("holds", holds, int(row["holds"]))]:
            check(mine == theirs, f"{key} {name}: recomputed {mine} vs csv {theirs}")
        res[key] = dict(set=case["set"], elig=case.get("eligibility", {}), valid=valid, effects=effects,
                        dispatches=dispatches, complete=complete, holds=holds, adopted=adopted, wait=wait)

    report = {}
    expected_n = oracle["metrics"]["denominators_per_policy"]
    for pol in POLICIES:
        v = [x for (c, p), x in res.items() if p == pol and x["set"] == "primary"]
        e = lambda flag: [x for x in v if x["elig"][flag]]  # noqa: E731
        m = {
            "duplicate_effect_rate": (sum(x["effects"] > 1 for x in v), len(v)),
            "correct_recovery_decision_rate": (sum(x["valid"] for x in v), len(v)),
            "recovery_completion_rate": (sum(x["complete"] for x in e("safely_recoverable")), len(e("safely_recoverable"))),
            "hindsight_completion_rate": (sum(x["complete"] for x in e("hindsight_recoverable")), len(e("hindsight_recoverable"))),
            "unnecessary_hold_rate": (sum(x["holds"] > 0 for x in e("unnecessary_hold_eligible")), len(e("unnecessary_hold_eligible"))),
            "required_hold_compliance": (sum(x["holds"] > 0 for x in v if x["elig"]["hold_class"] in ("required", "information_forced")),
                                         sum(x["elig"]["hold_class"] in ("required", "information_forced") for x in v)),
            "information_forced_holds": (sum(x["holds"] > 0 for x in v if x["elig"]["hold_class"] == "information_forced"),
                                         sum(x["elig"]["hold_class"] == "information_forced" for x in v)),
        }
        for name, (n, N) in m.items():
            s = summary["metrics_per_policy"][pol][name]
            check((s["n"], s["N"]) == (n, N), f"{pol} {name}: recomputed {n}/{N} vs summary {s['n']}/{s['N']}")
            check(N == expected_n[name], f"{pol} {name}: N {N} != frozen {expected_n[name]}")
        totals = {"dispatches": sum(x["dispatches"] for x in v), "committed_effects": sum(x["effects"] for x in v),
                  "adopted": sum(x["adopted"] for x in v), "holds": sum(x["holds"] for x in v),
                  "simulated_wait_s": sum(x["wait"] for x in v)}
        s = summary["metrics_per_policy"][pol]
        check(totals["dispatches"] == s["dispatches_total"], f"{pol} dispatches")
        check(totals["committed_effects"] == s["committed_effects_total"], f"{pol} effects")
        check(totals["simulated_wait_s"] == s["simulated_wait_s_total"], f"{pol} wait")
        report[pol] = {**{k: f"{n}/{N}" for k, (n, N) in m.items()}, **totals}

    b2 = {c: x for (c, p), x in res.items() if p == "B2" and x["set"] == "primary"}
    pp = {c: x for (c, p), x in res.items() if p == "P" and x["set"] == "primary"}
    same = [c for c in b2 if all(b2[c][k] == pp[c][k] for k in ("effects", "valid", "complete", "holds", "adopted", "dispatches"))]
    stress = {f"{c}/{p}": x["effects"] for (c, p), x in res.items() if x["set"] == "stress"}
    check(len(pipe) == 18, f"pipeline rows {len(pipe)} != 18")
    check(all(r["matches_service_level"] == "True" for r in pipe), "pipeline row does not match service level")
    masked = [f"{r['case_id']}/{r['policy']}" for r in pipe if r["graph_outcome"] == "graph_success" and r["committed_effects"] == "2"]

    print(json.dumps({
        "records": len(raw), "combinations": len(by), "primary": n_primary, "stress": len(by) - n_primary,
        "metrics_per_policy": report,
        "b2_p_identical_primary_cases": f"{len(same)}/13", "b2_p_differing": sorted(set(b2) - set(same)),
        "stress_effects": stress,
        "pipeline_rows": len(pipe), "pipeline_graph_success_with_two_effects": masked,
        "problems": problems,
    }, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
