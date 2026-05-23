# Workflow Summary

The prototype follows a staged supervisory workflow:

```text
Goal -> Planner -> Matcher -> Governance -> Execution -> Result
```

Each stage receives a structured object and returns a structured object for the
next stage. This keeps planning, capability selection, policy evaluation, and
execution separate and inspectable.

## Stage Description

1. **Goal:** A high-level operational request is provided as a `Goal` object.
   The payload carries operational context such as `machine_id` or
   `action_name`.
2. **Planner:** The `PlannerAgent` converts the goal into an ordered plan of
   human-readable and machine-usable steps.
3. **Matcher:** The `CapabilityMatchingAgent` maps steps with required
   capabilities to the YAML capability registry.
4. **Governance:** The `GovernanceAgent` evaluates each mapped step before
   execution and assigns an explicit policy decision.
5. **Execution:** The `ExecutionAgent` respects governance decisions, invokes
   adapters only for allowed executable steps, and records all other steps as
   skipped, blocked, approval-required, fallback-pending, or safe-aborted.
6. **Result:** The final execution result contains status counts, governance
   summary data, adapter outputs, and per-step outcomes.

## Mermaid View

```mermaid
flowchart LR
    A[Goal] --> B[PlannerAgent]
    B --> C[Plan]
    C --> D[CapabilityMatchingAgent]
    D --> E[MappedPlan]
    E --> F[GovernanceAgent]
    F --> G[GovernanceEvaluation]
    G --> H[ExecutionAgent]
    H --> I[ExecutionResult]
```

This workflow is deterministic in the current prototype. No LLM calls,
external systems, databases, or live industrial hardware are used.
