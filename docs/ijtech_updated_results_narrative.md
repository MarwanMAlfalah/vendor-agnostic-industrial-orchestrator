# IJTech Updated Results Narrative

## Results Paragraph

The empirical evidence now combines deterministic local evaluation with containerized and local
Kubernetes reproducibility artifacts. In the 240-scenario synthetic journal profile, the
`reference_v1` runtime achieved policy compliance of `0.8542`, unsafe execution of `0.0`, final
outcome accuracy of `0.875`, trace completeness of `1.0`, and p95 latency of `0.075116 ms`.
The `langgraph_runtime` achieved policy compliance of `0.9792`, unsafe execution of `0.0`, final
outcome accuracy of `0.9792`, trace completeness of `1.0`, and p95 latency of `3.815129 ms`.
The Docker Compose integration artifact adds five deterministic service-boundary cases using
containerized OPC UA-style, REST, and legacy mock services, with adapter contract pass rate
`1.0`, policy compliance `1.0`, unsafe execution `0.0`, final outcome accuracy `1.0`, and trace
completeness `1.0`. The actual local kind reproducibility artifact records completed Kubernetes
jobs, health endpoint availability, checkpoint PVC use, and crash/restart demo success as `true`,
with trace completeness `1.0`. These artifacts strengthen the engineering reproducibility evidence
for the prototype while preserving the original scope: deterministic synthetic and mock-service
experiments rather than production industrial deployment.

## Limitations Paragraph

The additional engineering evidence does not change the scientific claim boundary. Docker and
Kubernetes artifacts demonstrate local reproducibility and containerized deployment feasibility,
not production deployment, high availability, cybersecurity readiness, real-time guarantees, or
industrial certification. The OPC UA-style, REST, and legacy services used in the Docker demo are
deterministic mock services and integration proxies, not live PLCs, SCADA systems, or vendor
certified controllers. LangSmith traces and metadata support observability, debugging, and
inspection of deterministic execution structure, but they do not validate industrial safety,
regulatory compliance, physical process behavior, or live plant integration. GitHub Actions CI
success is software quality automation evidence only and does not validate industrial operation.

## Recommended Manuscript Insertion Points

1. Methods / Implementation: add a short paragraph describing three execution evidence layers:
   local deterministic evaluation, Docker Compose mock-service integration, and local Kubernetes
   reproducibility manifests.
2. Results: insert the results paragraph above after the main scaled-evaluation table, making clear
   that Docker and Kubernetes evidence are engineering reproducibility artifacts rather than new
   production-deployment results.
3. Reproducibility Package: cite `data/results/deployment_mode_comparison.csv` and
   `data/results/evidence_manifest.json` as the artifact index for local, Docker, Kubernetes,
   LangSmith, and CI-configuration evidence.
4. Threats to Validity: insert the limitations paragraph above, especially the non-claims about
   production deployment, live PLCs, certified safety, and LangSmith observability.
5. Appendix / Supplement: include the reproducibility evidence table from
   `docs/ijtech_reproducibility_evidence_table.md`.
