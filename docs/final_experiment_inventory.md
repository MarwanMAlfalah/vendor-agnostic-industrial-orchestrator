# Final Experiment Inventory

| Experiment | Runner Command | Input Cases | Output Files | Main Metrics | Interpretation | Suggested Figure/Table |
| --- | --- | --- | --- | --- | --- | --- |
| Canonical governance and baseline comparison | `.venv/bin/python -m app.evaluation.run_comparison` | 12 canonical cases: allow, approval, block, safe abort | `data/results/comparison_results.csv`, `data/results/baseline_summary.json`, `docs/comparison_summary.md` | policy compliance, unsafe execution, governance accuracy, final outcome accuracy, execution coverage | Shows reference governance is safer than simple baselines despite lower raw coverage. | Table: baseline vs reference policy metrics. |
| LangGraph canonical comparison | `.venv/bin/python -m app.evaluation.run_langgraph_comparison` | Same 12 canonical cases | `data/results/langgraph_comparison_results.csv`, `docs/langgraph_comparison_summary.md` | policy compliance, unsafe execution, trace completeness, resume success | Shows `langgraph_runtime` preserves reference correctness on canonical cases. | Figure: runtime parity table. |
| Mixed workflow comparison | `.venv/bin/python -m app.evaluation.run_mixed_workflow_comparison` | 12 mixed multi-step cases | `data/results/mixed_comparison_results.csv`, `docs/mixed_workflow_comparison_summary.md` | trace stage coverage, interrupt trace quality, final outcome accuracy | Shows LangGraph adds graph-stage trace value beyond correctness parity. | Figure: mixed workflow trace diagram. |
| Post-approval continuation | `.venv/bin/python -m app.evaluation.run_post_approval_comparison` | 6 approval-continuation cases | `data/results/post_approval_comparison_results.csv`, `docs/post_approval_comparison_summary.md` | approval validation accuracy, approved step execution rate, gated policy compliance | Shows valid approval can execute gated steps after revalidation while invalid cases remain safe. | Figure: approval continuation trace. |
| Crash/restart persistence demo | `.venv/bin/python -m app.evaluation.run_crash_restart_demo` | 2 approval checkpoint cases | `data/results/crash_restart_demo_summary.json`, `docs/crash_restart_demo.md`, `data/langgraph/checkpoints.db` | checkpoint resume, restart recovery, post-restart outcome accuracy, trace completeness | Shows restart-safe continuation from a persisted approval checkpoint. | Figure: checkpoint/resume sequence. |
| LangSmith trace examples | No separate runner; enabled by env vars during the above commands | All traced experiment runs | `docs/langsmith_trace_examples.md`, hosted LangSmith traces | structured trace outputs, span names, screenshot guidance | Shows how observability supports debugging and paper figures. | Screenshot: LangSmith span tree and outputs panel. |
| Unified research package | Generated from existing result artifacts | All evaluation layers | `data/results/final_unified_metrics.csv`, `data/results/final_unified_metrics.json`, `docs/final_unified_evaluation_report.md` | consolidated metrics across all layers | Provides manuscript-ready summary of evidence. | Table: unified metric summary. |

## Reproducibility Notes

All runner output filenames are fixed. Policy metrics are deterministic. Local
timing values can vary slightly by machine and run.

