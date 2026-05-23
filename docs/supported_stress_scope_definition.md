# Supported And Stress Scope Definition

Scope is runtime-specific.

- `post_approval_valid` is supported scope for `langgraph_runtime`.
- Post-approval continuation is stress/out-of-scope for `reference_v1`.
- Malformed payload, unavailable capability, and unsupported capability cases
  are stress scope for all runtimes unless explicitly supported.
- Unsafe blocked-action cases are supported scope for governance-aware runtimes
  because blocking unsafe actions is an intended capability.
- Direct unsafe execution cases are expected failure/stress cases for baselines.

Stress cases are retained and reported separately. They are not deleted or
hidden.
