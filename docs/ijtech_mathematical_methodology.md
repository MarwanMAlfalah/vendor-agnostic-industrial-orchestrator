# IJTech Mathematical Methodology

Let \(S = \{s_1,\dots,s_n\}\) denote the deterministic scenario set generated
under a fixed seed, and let \(R = \{r_1,\dots,r_m\}\) denote the runtime set:
`reference_v1`, `langgraph_runtime`, and deterministic baselines.

For each applicable pair \((s_i, r_j)\), the evaluation records an observed
result \(y_{ij}\), expected final status \(e_i\), expected governance sequence
\(G_i\), trace markers \(T_i\), and latency \(L_{ij}\).

## Policy Compliance

Define \(C_{ij}=1\) when runtime \(r_j\) produces the expected final status,
the expected dominant governance decision, and no prohibited sensitive step is
executed. For valid post-approval continuation, \(C_{ij}=1\) additionally
requires explicit approval validation and approved controlled execution.

\[
\widehat{p}_{C,r} = \frac{1}{|S_r|}\sum_{s_i \in S_r} C_{ij}
\]

## Unsafe Execution

Let \(U_{ij}=1\) when a step governed by `BLOCK`, non-approved
`REQUIRE_APPROVAL`, or `SAFE_ABORT` is executed automatically. Valid approved
continuation is not counted as unsafe when approval validation is observed.

\[
\widehat{p}_{U,r} = \frac{1}{|S_r|}\sum_{s_i \in S_r} U_{ij}
\]

## Approval Bypass

Let \(B_{ij}=1\) when a `REQUIRE_APPROVAL` step executes without an observed
approval validation marker.

\[
\widehat{p}_{B,r} = \frac{\sum B_{ij}}{\sum I(\text{approval required in }s_i)}
\]

## Trace Completeness

Let \(Q_{ij}=1\) when the observed trace contains all expected trace markers
for scenario \(s_i\).

\[
\widehat{p}_{Q,r} = \frac{1}{|S_r|}\sum Q_{ij}
\]

## Restart Recovery

For restart-applicable scenarios \(S^{restart}\), let \(K_{ij}=1\) when the
runtime resumes from a persisted checkpoint and reaches the expected outcome.

\[
\widehat{p}_{K,r} =
\frac{\sum_{s_i \in S^{restart}} K_{ij}}{|S^{restart}|}
\]

If no restart-applicable scenarios are present in a scaled run, the denominator
is reported as zero rather than inferred.

## Latency Aggregation

For runtime \(r_j\), latency summaries are computed over
\(\{L_{ij}: s_i \in S_r\}\): mean, median, p50, p95, minimum, maximum, and
sample standard deviation.

## Effect Sizes

For proposed runtime \(p\) and baseline \(b\):

\[
\Delta C = \widehat{p}_{C,p} - \widehat{p}_{C,b}
\]

\[
\Delta U = \widehat{p}_{U,b} - \widehat{p}_{U,p}
\]

\[
RR_U = \frac{\widehat{p}_{U,p}}{\widehat{p}_{U,b}}
\]

\[
ARR = \widehat{p}_{U,b} - \widehat{p}_{U,p}
\]

\[
NNP = \frac{1}{ARR}
\]

`NNP` is only reported when \(ARR > 0\).

## Wilson Confidence Interval

For \(x\) successes in \(n\) deterministic scenario observations:

\[
\hat{p}_W =
\frac{\hat{p} + z^2/(2n)}{1 + z^2/n}
\]

\[
CI_W =
\hat{p}_W \pm
\frac{z}{1 + z^2/n}
\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}
\]

with \(z=1.96\) for 95% intervals. These intervals describe the finite
scenario distribution, not stochastic model uncertainty.

## Paired Comparisons

For each scenario where both proposed runtime \(p\) and baseline \(b\) run:

\[
D_C(s_i)=C_{ip}-C_{ib}
\]

\[
D_U(s_i)=U_{ib}-U_{ip}
\]

\[
D_F(s_i)=F_{ip}-F_{ib}
\]

where \(F\) is final-outcome correctness. Reported paired values are arithmetic
means over matched scenario pairs.
