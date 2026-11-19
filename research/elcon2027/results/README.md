# ElCon-EE 2027 results index

Evidence label for all runs here: **In-repository, service-level deterministic simulation**
(protocol v1.0, frozen at `33ea97cc6585caf9ea294317b82f93d813c40d21`). Each run directory has
its own `manifest.json` (code revision, uncommitted-code hashes, protocol hashes, command,
output hashes).

| Run | Status | Note |
|---|---|---|
| `20261110T124221Z-33ea97c` | superseded (reporting only) | First run. In its pipeline cross-check table, `workflow_status=completed` means "the LangGraph run reported success", not protocol completion (which also requires exactly one committed effect). Decision latency was not summarised. |
| `20261110T124324Z-33ea97c` | superseded (identical outcomes) | Same code apart from those two reporting fixes. `trials.csv` rows identical to the first run, excluding wall-clock `latency_ns` (60/60). Produced with uncommitted code (hashes in its manifest). |
| `20261110T132939Z-fb77698` | **authoritative (reported in the ElCon-EE 2027 manuscript)** | Produced by committed code at `fb77698` with no uncommitted code. `trials.csv` identical to `20261110T124324Z-33ea97c` excluding `latency_ns` (60/60). Independently recomputed by `../submission_v2/release_candidate/verification/verify_results.py` (exit 0; recorded output in `verify_output.json` beside it). A rerun from a clean clone of `fb77698` on 2026-11-11, written outside the repository, reproduced 60/60 trial rows and 18/18 pipeline rows; that rerun needs the local commit `fb77698` and its record is not published. |

No run directory has been edited after it was written. Of the reproducibility bundle `../submission_v2/release_candidate/`, only the `verification/` folder is published; its other files duplicate the published protocol and run, archive the `fb77698` source, or are manuscript material. The pipeline cross-check is opt-in
LangGraph integration evidence. It is reported in its own table and is not part of the 52-trial
service-level evaluation.

**Publication note.** The commits named above (`33ea97c`, `fb77698`) are local research commits.
They are not part of this repository's public history: the protocol, code, and run directories
were copied into a later publication snapshot byte-for-byte. Which checks a reader can and cannot
perform without those commits is listed in `../PUBLICATION_PROVENANCE.md`.
