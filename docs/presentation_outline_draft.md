# Presentation Outline Draft

## Slide 1: Title
- Vendor-Agnostic Supervisory Orchestration for Industrial Operations
- Research prototype and deterministic evaluation

## Slide 2: Motivation
- Industrial operations involve heterogeneous systems and vendor-specific tools.
- Supervisory orchestration needs clear separation between planning, policy,
  and execution.

## Slide 3: Prototype Scope
- Python and FastAPI backend.
- Deterministic agents, mock adapters, YAML capability registry.
- No live hardware, database, LLM execution, or production deployment.

## Slide 4: Core Workflow
- Goal -> Planner -> Matcher -> Governance -> Execution -> Result.
- Each stage exchanges structured data contracts.

## Slide 5: Adapter Abstraction
- OPC UA adapter for mock industrial reads.
- REST adapter for mock service workflows.
- Legacy adapter for vendor-specific operations.

## Slide 6: Governance Layer
- Decisions: ALLOW, REQUIRE_APPROVAL, BLOCK, FALLBACK, SAFE_ABORT.
- Execution respects governance decisions before invoking adapters.

## Slide 7: Evaluation Design
- 12 deterministic runs.
- 3 ALLOW, 3 REQUIRE_APPROVAL, 3 BLOCK, 3 SAFE_ABORT cases.

## Slide 8: Results
- Success: 3 / 12.
- Partial success: 3 / 12.
- Blocked: 3 / 12.
- Safe aborted: 3 / 12.
- Failed: 0 / 12.

## Slide 9: Interpretation
- The prototype demonstrates structured governance-aware execution.
- Adapter calls occur only when explicitly allowed.
- The evaluation checks control-flow behavior, not industrial performance.

## Slide 10: Next Steps
- Add richer scenario definitions and traces.
- Add approval and fallback workflows.
- Expand adapter realism and validation coverage.
- Explore LLM-assisted planning under deterministic governance constraints.
