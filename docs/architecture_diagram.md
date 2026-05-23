# Architecture Diagram

```mermaid
flowchart TB
    API[API Layer]
    Registry[Capability Registry]
    Planner[Planner Agent]
    Matcher[Capability Matching Agent]
    Governance[Governance Agent]
    Execution[Execution Agent]
    Factory[Adapter Factory]
    OPCUA[OPC UA Adapter]
    REST[REST Adapter]
    Legacy[Legacy Adapter]
    Evaluation[Evaluation Runner / Results]

    API --> Planner
    API --> Matcher
    API --> Governance
    API --> Execution
    Matcher --> Registry
    Governance --> Registry
    Execution --> Factory
    Factory --> OPCUA
    Factory --> REST
    Factory --> Legacy
    Evaluation --> Execution
    Evaluation --> Results[(CSV / JSON Results)]
```

The architecture uses a FastAPI layer for manual testing and inspection.
Planning, matching, governance, and execution are implemented as separate
deterministic agents. The capability registry provides adapter metadata and
policy tags. The execution agent invokes mock adapters through the adapter
factory only after governance decisions have been applied. The evaluation runner
uses the same execution path and exports structured CSV and JSON results.
