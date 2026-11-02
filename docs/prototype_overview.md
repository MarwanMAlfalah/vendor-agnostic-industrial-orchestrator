# Prototype Overview (Historical)

This document describes the earlier reference-only prototype. It is retained as
historical context: the current repository includes LangGraph, SQLite checkpoint
persistence, and Docker/Kubernetes configuration. See [README](../README.md)
for current runtime capabilities.

This project implements a minimal supervisory research prototype for a
vendor-agnostic industrial orchestrator. The prototype studies how a high-level
operational goal can be translated into a deterministic plan, mapped to
registered capabilities, evaluated by governance rules, and executed through
mock heterogeneous adapters.

The implementation is intentionally limited in scope. It does not include a
database, frontend, LLM calls, LangGraph, deployment configuration, or live
industrial connectivity. Its purpose is to provide a clean backend structure for
experimentation with orchestration contracts, governance-aware execution, and
adapter abstraction.

## Main Components

- **FastAPI backend:** exposes manual inspection and testing endpoints for
  health checks, capabilities, planning, matching, governance evaluation, and
  execution.
- **PlannerAgent:** converts supported high-level goals into ordered,
  deterministic plan steps.
- **CapabilityMatchingAgent:** maps plan steps to registered capabilities from
  the YAML capability registry.
- **GovernanceAgent:** evaluates mapped steps using explicit deterministic
  policy rules before execution.
- **ExecutionAgent:** executes only governance-allowed adapter-backed steps and
  records skipped, blocked, approval-required, and safe-aborted steps.
- **Evaluation runner:** executes a controlled batch of governance-aware
  scenarios and exports CSV, JSON, and summary metrics.

## Adapter Types

The prototype includes three mock adapter types behind a common invocation
interface:

- **OPCUAAdapter:** represents industrial read operations such as reading
  machine status and alarm codes.
- **RESTAdapter:** represents service-oriented operations such as maintenance
  ticket creation and ticket-status queries.
- **LegacyAdapter:** represents vendor-specific or legacy operations, including
  vendor action validation and legacy command execution.

Each adapter returns normalized dictionaries while preserving distinct internal
behavior. This provides a simple foundation for later adapter expansion without
coupling orchestration logic to vendor-specific implementations.

## Core Execution Flow

The implemented flow is:

1. A `Goal` is submitted with a goal type, target, priority, requester,
   timestamp, and payload.
2. The planner returns an ordered `Plan` while preserving the original payload.
3. The matcher maps required capabilities to registry-backed adapter
   capabilities and produces a `MappedPlan`.
4. Governance evaluates each mapped step and assigns a decision such as
   `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, or `SAFE_ABORT`.
5. Execution invokes adapters only for allowed executable steps and returns a
   structured `ExecutionResult`.

The current prototype emphasizes traceable control flow and deterministic
policy behavior rather than autonomous decision-making.
