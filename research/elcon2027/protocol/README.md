# ElCon-EE 2027 recovery protocol

| | |
|---|---|
| Protocol version | 1.0 |
| Status | FROZEN 2026-11-09 |
| Evidence label | In-repository, service-level deterministic simulation |
| Branch / parent of anchor commit | `research/elcon2027-recovery` / `a0fe2f612c4814a6b6b1891ec5cd84cb8c89c26a` |
| Anchor | the local commit that first contains this file at version 1.0 |
| Environment at freeze | Python 3.11.0, SQLite 3.38.4, Darwin 25.5.0 |
| Results generated | none |

## Files

- `protocol.md`: observation, time semantics, matrix, policies, oracle, metrics, reproducibility
  and development history, freeze record, limitations.
- `oracle_table.json`: authoritative pre-specified oracle (13 primary + 2 stress cases), with
  metric metadata.
- `service_review.md`: effect-service reviews, acceptance traceability, resolutions.
- `SHA256SUMS`: checksums of the four files above.

## Code under test at freeze

```
72b7fd57173da05c15d5df5103025b458275a6a35e74ab150d25d81f973370ac  app/integration/maintenance_effect_service.py
24512aa1021e193018c8ef16af8f81eb9e587193a7a421cf9e394c372746619c  tests/test_maintenance_effect_service.py
0384f7e55d3e6e8bdd272e7593035adac833e1686e1cc1c5c61efeed32a1dc47  tests/test_elcon_protocol_oracle.py
```

## Approved reviewer decisions (2026-11-09)

1. **B2** holds when the outcome is uncertain and there is neither deduplication nor authoritative
   verification. With service deduplication it retries with the same operation ID and identical
   parameters (same fingerprint).
2. **P** never reads an inconclusive `not_found` as absence. Without declared visibility **and**
   completion bounds it holds, unless the effect is positively confirmed (ADOPT is valid without
   a bound) or the service deduplicates.
3. **C11a and C12** are concurrency stress cases, outside the 13-case primary comparison.
   Single-active-resumer is not enforced.
4. **Evidence label:** In-repository, service-level deterministic simulation.

## Using the frozen protocol

1. The runner (not yet implemented) verifies `shasum -a 256 -c SHA256SUMS` in this directory and
   refuses to run on mismatch.
2. Every `run_metadata.json` records the anchor commit SHA, protocol version, and the SHA-256 of
   `oracle_table.json` and of `SHA256SUMS` (which cannot list its own hash).
3. Any change to these files creates version 1.1+. Results are labelled with their protocol
   version, and deviations are logged in `DEVIATIONS.md`.
