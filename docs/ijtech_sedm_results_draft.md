# Results Draft

## Canonical Governance Comparison

The canonical comparison evaluates 12 deterministic cases covering allowed actions, approval-required actions, blocked actions, and safe-abort conditions. In these controlled cases, the reference governance-aware execution path achieves policy compliance of 1.0, unsafe execution of 0.0, governance decision accuracy of 1.0, and final outcome accuracy of 1.0. The deterministic baselines show why raw execution success is insufficient. Baseline B, for example, reaches execution coverage of 1.0 in the unified table but has policy compliance of 0.25 and unsafe execution of 1.0. This supports the claim that policy-centric metrics are necessary for governed industrial workflows.

## Scaled Journal Profile

The journal scaled profile contains 240 deterministic scenarios. Original and aligned metrics are both reported. Under the original global labels, `reference_v1` has policy compliance of 0.854167 and final outcome accuracy of 0.875, while `langgraph_runtime` has policy compliance and final outcome accuracy of 0.979167. The aligned evaluation corrects runtime-capability mismatches by evaluating `reference_v1` as a non-continuation runtime and `langgraph_runtime` as a controlled-continuation runtime. Under aligned expectations, both proposed runtimes achieve policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, approval bypass of 0.0, invalid mapping containment of 1.0, and trace completeness of 1.0.

## Baseline Comparison

The aligned journal comparison shows substantial separation between governance-aware runtimes and governance-ablated baselines. Baseline A, direct execution without governance, has aligned policy compliance of 0.0, unsafe execution of 0.583333, approval bypass of 0.5, and trace completeness of 0.0. Baseline C, without policy filtering, has aligned policy compliance of 0.416667 and unsafe execution of 0.583333. Baseline B avoids unsafe execution in this aligned table but has aligned policy compliance of only 0.083333 and final outcome accuracy of 0.166667. These results indicate that removing governance or architectural stages can produce technically completed executions that do not satisfy policy requirements.

## Supported Versus Stress Scope

The aligned supported/stress split is runtime-specific. For `reference_v1`, supported-scope scenarios have aligned policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, and trace completeness of 1.0. Its stress-scope rows also show aligned containment of 1.0, reflecting that the alignment treats post-approval continuation as outside its capability profile while preserving containment expectations. For `langgraph_runtime`, supported-scope and stress-scope rows both show aligned policy compliance of 1.0, unsafe execution of 0.0, and trace completeness of 1.0. Baselines remain weak in stress scope, especially Baseline A and Baseline C, where unsafe execution is 0.636364 and 0.777778 respectively in the aligned supported/stress table.

## LangGraph Approval Continuation

The post-approval continuation experiment distinguishes stopping at an approval checkpoint from controlled continuation after explicit approval. `reference_v1` is policy-correct as a non-continuation runtime but does not execute gated steps after approval. `langgraph_runtime` supports approval interrupt/resume, approval validation, revalidation of mapping eligibility, and controlled execution of approved steps. In the unified report, the LangGraph post-approval comparison reports 1.0 for approval validation accuracy, approved step execution rate, post-resume final outcome accuracy, gated step policy compliance, and approved execution trace completeness.

## Crash/Restart Persistence

The crash/restart persistence demo uses a SQLite LangGraph checkpointer. It demonstrates that a workflow can reach an approval interrupt, persist checkpoint state, simulate process stop, reopen the runtime with the same checkpoint database and thread identifier, resume with approval input, and reach the expected final result. The unified report records checkpoint resume success, restart recovery success, post-restart final outcome accuracy, and restart trace completeness as 1.0 for this demo. This is local persistence evidence, not production deployment evidence.

## LangSmith Observability

LangSmith tracing is used as optional observability evidence. It records experiment-level and child span outputs for stages such as planning, matching, governance, approval interrupt, approval resume, approved execution, execution, and final result. These traces support debugging, auditability, and figure preparation. They do not validate industrial deployment or certified safety.
