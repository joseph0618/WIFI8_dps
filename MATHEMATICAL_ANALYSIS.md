# Mathematical analysis of UL trigger-based DPS

This document explains the saturated approximation in `src/dps_sim/analytical.py`. The [LaTeX companion](MATHEMATICAL_ANALYSIS.tex) provides the detailed mathematical derivation. Both describe the current HC DPS model.

## 1. Operation and assumptions

Each packet requires two separate contention wins:

1. The STA wins a TXOP and sends EBSR on LC. It then stops contending while waiting for service.
2. The AP wins a later TXOP and serves the oldest report: ICF on LC, switch up, ICR–DATA–ACK on HC, switch down to LC.

The AP is one contender whenever reports are pending, regardless of their number. Each grant serves one packet, FIFO. Other eligible STAs can contend between the report and its grant.

The approximation assumes saturation, identical contention parameters, one serialized channel, unlimited retries, capped backoff stages, no PHY errors, and equal EBSR/ICF lengths. Backoff counters freeze during busy periods. Switching occupies channel time and does not overlap interframe gaps. Only the selected STA switches to HC; AP energy is excluded. These are research assumptions, not a complete IEEE implementation.

## 2. Notation and units

| Symbol | Meaning | Default |
|---|---|---:|
| \(N\) | Number of STAs | Varied |
| \(W,m\) | Initial contention window size; maximum stage | 32, 5 |
| \(\sigma,s,d,\delta\) | Slot, SIFS, DIFS, propagation | 50, 28, 128, 1 μs |
| \(L,h\) | Payload; DATA header | 8184, 400 bits |
| \(e,f,r,a\) | EBSR, ICF, ICR, ACK including PHY | 288, 288, 240, 240 bits |
| \(R_C,R_H\) | Control; HC DATA rate | 1, 10 Mbps |
| \(u,v\) | Switch-up; switch-down time | 100, 100 μs |
| \(P_{L,i},P_{L,r},P_{L,t}\) | LC idle, RX, TX power | 0.10, 0.20, 0.50 W |
| \(P_{H,i},P_{H,r},P_{H,t},P_{sw}\) | HC idle, RX, TX, switching power | 0.30, 0.50, 1.00, 0.40 W |

All durations below use μs. Rates in Mbps equal bits/μs. Let \(\gamma=10^{-6}\) convert μs to seconds in energy calculations.

## 3. State-dependent contention

Let \(k\in\{0,\ldots,N\}\) be the number of reported STAs awaiting service. The eligible STA population is \(n_k=N-k\), and the total active population is

\[
M_k=N-k+\mathbf1_{\{k>0\}}.
\]

Local Bianchi decoupling assigns each active contender the same attempt probability \(\tau_k\) and conditional collision probability \(p_k\):

\[
p_k=1-(1-\tau_k)^{M_k-1},\qquad
\tau_k=\frac{2}{W+1+Wp_k\sum_{j=0}^{m-1}(2p_k)^j}.
\]

The finite sum avoids a removable singularity at \(p_k=1/2\). For \(m=0\), it is empty. With one contender, \(p_k=0\) and \(\tau_k=2/(W+1)\).

The true system also retains counters, retry stages, and FIFO identities. Thus the reduced state \(k\) is an approximation, not an exact Markov description of the simulator.

## 4. Events and stationary distribution

A virtual event is an idle countdown slot, successful EBSR, successful AP exchange, or collision:

\[
\begin{aligned}
P_0(k)&=(1-\tau_k)^{M_k},\\
P_E(k)&=(N-k)\tau_k(1-\tau_k)^{M_k-1},\\
P_A(k)&=\mathbf1_{\{k>0\}}\tau_k(1-\tau_k)^{M_k-1},\\
P_C(k)&=1-P_0(k)-P_E(k)-P_A(k).
\end{aligned}
\]

A successful report increments \(k\), while AP success decrements it. Idle and collision are self-loops. The birth–death stationary distribution satisfies

\[
\pi_{k+1}=\pi_k\frac{P_E(k)}{P_A(k+1)},\qquad
\pi_k=\frac{w_k}{\sum_{\ell=0}^{N}w_\ell},\quad
w_k=\prod_{j=0}^{k-1}\frac{P_E(j)}{P_A(j+1)},\quad w_0=1.
\]

The implementation normalizes log weights for numerical stability. Flow conservation requires

\[
q_E=\sum_k\pi_kP_E(k)=\sum_k\pi_kP_A(k)=q_A.
\]

## 5. Holding times and throughput

The channel holding times, including trailing gaps, are

\[
\begin{aligned}
T_E&=e/R_C+d+\delta,\\
T_U&=(f+r+a)/R_C+(h+L)/R_H+3s+d+4\delta+u+v,\\
T_C&=e/R_C+d+\delta\qquad(e=f).
\end{aligned}
\]

The AP exchange includes all four frames, three SIFS, propagation, both switches, and trailing DIFS. ICR and ACK keep control rate \(R_C\) despite HC operation. Equal EBSR/ICF airtime makes the collision holding time fixed.

Define

\[
t_k=P_0(k)\sigma+P_E(k)T_E+P_A(k)T_U+P_C(k)T_C,
\qquad\bar t=\sum_k\pi_kt_k.
\]

Each AP success delivers \(L\) payload bits, so

\[
S=\frac{Lq_A}{\bar t}\ \mathrm{Mbps},\qquad
C_{packet}=\frac{\bar t}{1000q_A}\ \mathrm{ms}.
\]

The second quantity is aggregate channel cost per delivery, **not arrival-to-ACK packet delay**.

## 6. Collision ratio per transmission

Expected total attempts per virtual event are \(A_k=M_k\tau_k\). A successful contention contains one attempt, hence

\[
C_k=A_k-P_E(k)-P_A(k)=A_kp_k,
\qquad
\boxed{\rho=\frac{\sum_k\pi_kC_k}{\sum_k\pi_kA_k}}.
\]

This is an attempt-weighted conditional collision probability. It is neither an unweighted average of \(p_k\) nor collision events per second. Three colliding senders contribute three collided attempts. Successful EBSR and ICF each count once; protected ICR/DATA/ACK do not contend separately.

## 7. Time occupancy and channel fractions

Longer events occupy more time, so embedded-event and elapsed-time probabilities differ:

\[
\omega_k=\frac{\pi_kt_k}{\bar t},\qquad\overline K=\sum_k k\omega_k.
\]

The channel fractions are

\[
F_0=\frac{\sigma\sum_k\pi_kP_0(k)}{\bar t},\quad
F_U=\frac{T_Eq_E+T_Uq_A}{\bar t},\quad
F_C=\frac{T_C\sum_k\pi_kP_C(k)}{\bar t}.
\]

They sum to one. The success fraction includes successful-exchange overhead, not only payload airtime.

## 8. Energy rewards

All energy rewards include every STA, but exclude the AP. A successful report consumes

\[
E_E=\gamma\left[\frac e{R_C}\{P_{L,t}+(N-1)P_{L,r}\}+(d+\delta)NP_{L,i}\right].
\]

For compactness define

\[
\begin{aligned}
P_{Ht}&=P_{H,t}+(N-1)P_{L,r},&P_{Hr}&=P_{H,r}+(N-1)P_{L,r},\\
P_{Hi}&=P_{H,i}+(N-1)P_{L,i},&P_{Ss}&=P_{sw}+(N-1)P_{L,i}.
\end{aligned}
\]

The AP-exchange reward is

\[
E_U=\gamma\left[\frac f{R_C}NP_{L,r}+(s+\delta)NP_{L,i}
+\left(\frac r{R_C}+\frac{h+L}{R_H}\right)P_{Ht}
+\frac a{R_C}P_{Hr}+2(s+\delta)P_{Hi}
+(u+v)P_{Ss}+(d+\delta)NP_{L,i}\right].
\]

Other STAs use LC RX accounting during HC frames; this does not assert that they decode them.

The unconditional expected STA sender count in collision events is \(x_k=(N-k)\tau_k-P_E(k)\). With \(t_f=e/R_C\), the already probability-weighted collision contribution is

\[
\widetilde E_C(k)=\gamma\left[t_f\{x_kP_{L,t}+(NP_C(k)-x_k)P_{L,r}\}
+P_C(k)(d+\delta)NP_{L,i}\right].
\]

Do not multiply this term by \(P_C(k)\) again. Define

\[
E_k=P_0(k)\gamma\sigma NP_{L,i}+P_E(k)E_E+P_A(k)E_U+\widetilde E_C(k),
\qquad\bar E=\sum_k\pi_kE_k.
\]

Then

\[
\overline P_{STA}=\frac{\bar E}{N\gamma\bar t}\ \mathrm W,
\qquad E_{packet}=1000\frac{\bar E}{q_A}\ \mathrm{mJ}.
\]

Energy per delivered packet includes network-wide STA waiting and overhearing, not only its transmitter's energy.

## 9. Intervening transmissions after EBSR

For completed pair \(j\), let \(B_j\) be the cumulative network contention-attempt counter immediately after successful EBSR, and \(G_j\) the counter including its corresponding successful AP ICF. The simulator measures

\[
I_j=G_j-B_j-1,\qquad \overline I=\frac1D\sum_{j=1}^{D}I_j.
\]

Both endpoints are excluded. Other successful contentions and each collided sender count; protected responses do not count separately. Only ACK-completed pairs in the observation window enter the mean. No completed pair yields NaN; a single STA gives zero. Short windows can favor quickly completed pairs.

This metric is simulation-only: the analytical implementation does not retain a tagged report or FIFO position.

## 10. Checks and validation

For one STA there are no collisions. Each of two fresh uniform backoffs has mean \((W-1)/2\) slots, giving

\[
T_{cycle}=(W-1)\sigma+T_E+T_U,\qquad S=L/T_{cycle}.
\]

If all LC/HC/switch powers equal \(P\), then \(E_k=\gamma NPt_k\) and the predicted mean STA power is exactly \(P\). Additional checks cover probability normalization, report/service balance, and channel-fraction conservation.

```powershell
py -B tests/check_models.py
py -B validate_dps.py
```

Five scenarios, three station counts, and three seeds give 45 default runs, plus nine observation-window checks. See the [report](results/dps_validation/REPORT.md) and [comparison data](results/dps_validation/comparison.csv). Error bars are one standard error, not 95% confidence intervals. Zero-based plot axes do not change numerical errors.

The prediction is stationary, while simulation starts with no pending reports. Retained counter/stage history and initial transients can affect agreement. Close throughput agreement does not prove accurate collision dynamics. Poisson delay/PRR, tagged-report counts, analytical state occupancy, and PHY correctness are outside this validation.

The DCF fixed point follows the Bianchi decoupling approach (2000, DOI 10.1109/49.840210). The DPS state reduction and reward construction are this project's approximation.

## 11. Why saturated LC and HC DCF can have the same collision ratio

In both Bianchi baselines every saturated STA remains eligible. Their \(N,W,m\), counter-freezing rules, and contention random-number stream are identical. Therefore the sender sets at the same contention-event index are identical; changing the PHY rate changes the time spent on each event, not the sequence of backoff decisions.

For homogeneous DCF the conditional collision fixed point is

\[
p=1-(1-\tau)^{N-1}.
\]

The PHY rate is absent from this expression. It enters holding times, so HC can have more attempts and even more collision events per second while having the same collision ratio per attempt. Fixed-duration empirical ratios may differ because the two models observe different-length prefixes of the event sequence. The equality is specific to the saturated access assumptions; Poisson queues, errors, contention-window adaptation, or other MAC changes can break it.

DPS has \(M_k=N-k+\mathbf1_{\{k>0\}}\) active contenders rather than \(N\) always-active STAs. Reported STAs have withdrawn. Consequently there is no general reason for HC DCF's collision ratio to be smaller than DPS's.

## 12. Variable collision probabilities and transient analysis

The scalar stationary collision ratio does not imply that individual windows have constant collision statistics. In a more general time-dependent decoupling, eligible contender \(i\) has attempt probability \(\tau_i(j)\) at virtual-event index \(j\), giving

\[
p_i(j)=1-\prod_{\ell\ne i}(1-\tau_\ell(j)),\qquad
\rho(j)=\frac{\sum_i\tau_i(j)p_i(j)}{\sum_i\tau_i(j)}.
\]

This assumes independent attempts; retained backoff states and eligibility correlations make it an approximation. A complete transient model would include counters, retry stages, report membership and FIFO order in the state.

The implemented reduced transient uses the existing event transition matrix \(Q\). Starting with no reported STAs,

\[
\alpha_0=(1,0,\ldots,0),\qquad \alpha_{j+1}=\alpha_jQ.
\]

With the same \(A_k,C_k\) as before,

\[
a_j=\sum_k\alpha_j(k)A_k,\quad c_j=\sum_k\alpha_j(k)C_k,
\quad \rho_j=\frac{c_j}{a_j},\quad
\rho_{[0,J)}=\frac{\sum_{j=0}^{J-1}c_j}{\sum_{j=0}^{J-1}a_j}.
\]

These are ratios of expected counts, not expectations of a noisy sample-path ratio. In particular, averaging instantaneous ratios without their attempt weights generally gives a different answer.

The expected elapsed time after \(J\) virtual events is

\[
\mathbb E[T_J]=\gamma\sum_{j=0}^{J-1}\sum_k\alpha_j(k)t_k.
\]

Plotting against this expected time does not produce an exact physical-time transient: actual event durations and state trajectories are random. A time-domain prediction requires the full Markov-renewal holding-time treatment.

For this finite irreducible chain with self-loops, \(\alpha_j\) converges to \(\pi\), hence \(\rho_j\) converges to the stationary attempt-weighted ratio. Transient departures can decay; this is not mathematical divergence. Sample-window ratios can wiggle because of startup, retained backoff, and sampling noise. Sustained oscillation or failure to settle must be demonstrated rather than imposed. The investigation records the reduced chain's eigenvalues and compares window, cumulative, and warm-up-excluded empirical ratios.

`predict_dps_transient()` implements this **event-index local-equilibrium approximation for fixed-payload always-DPS**. It is not a new analytical model of the mixed threshold policy, and its local equilibrium does not capture the initial uniform-counter ensemble exactly.

## 13. Exact decomposition of EBSR-to-trigger waiting attempts

For completed pair \(j\), define \(q_j\) as the number of reports already ahead in the AP FIFO when its EBSR succeeds. Exactly those \(q_j\) grants must finish before its own grant. Let \(E_j\) count intervening successful EBSRs, \(D_j\) intervening direct DATA successes, and \(C_{E,j},C_{F,j},C_{D,j}\) the numbers of collided EBSR, ICF, and direct-DATA attempts. Then, for the current basic-access experiments,

\[
\boxed{I_j=q_j+E_j+D_j+C_{E,j}+C_{F,j}+C_{D,j}.}
\]

The identity counts each collided sender separately and excludes the tagged EBSR and tagged successful ICF. In always-DPS, \(D_j=C_{D,j}=0\). It is a network-wide waiting count; it is not the tagged STA's retry count. The tagged STA does not contend while waiting.

For each of the \(q_j\) intervening grants there is one successful ICF, one protected ICR, one HC DATA and one ACK. Therefore ICR contributes **zero contention attempts**, despite appearing as a transmitted frame. In mixed DPS, direct LC deliveries add DATA/ACK pairs. Contention-attempt share, transmitted-frame share, and channel-airtime share have different denominators and must be reported separately.

In a heavily backlogged always-DPS case, new reports approximately replenish served reports, so \(E_j\) can be close to \(q_j\). A rough explanatory scale is \(I_j\approx2q_j\) plus collided attempts. This is a heuristic, not a tagged-process prediction. A value around 100 for 50 STAs can therefore reflect FIFO waiting for many other stations rather than 100 failures by one station.

Run `py -B investigate_contention.py` for paired LC/HC event-sequence checks, per-kind attempt/frame ratios, FIFO decomposition, measured report-state occupancy, and collision-transient plots. Outputs are saved in [the investigation folder](results/contention_investigation/REPORT.md). Completed-pair censoring and finite-window effects remain explicit in its report.

## 14. AP/STA role asymmetry: what a richer model must retain

The measured per-kind collision ratios are not identical. With 50 STAs in the fixed-payload experiment, EBSR attempts collided about 9.96% of the time versus 5.39% for ICF attempts (full-window pooled counts). The current homogeneous local closure cannot resolve that role difference.

One possible extension assigns \(\tau_S(k,j)\) to eligible STAs and \(\tau_A(k,j)\) to the AP, with \(b_k=\mathbf1_{\{k>0\}}\). Under an independent-role approximation,

\[
\begin{aligned}
P_0(k,j)&=(1-\tau_S)^{n_k}(1-\tau_A)^{b_k},\\
P_E(k,j)&=n_k\tau_S(1-\tau_S)^{n_k-1}(1-\tau_A)^{b_k},\\
P_A(k,j)&=b_k\tau_A(1-\tau_S)^{n_k},\\
p_S(k,j)&=1-(1-\tau_S)^{n_k-1}(1-\tau_A)^{b_k},\\
p_A(k,j)&=1-(1-\tau_S)^{n_k}.
\end{aligned}
\]

Use the STA expressions only when \(n_k>0\), with \(P_E=0\) otherwise; the AP conditional expression applies only when it is active. Expected attempt and collided-attempt counts become

\[
A(k,j)=n_k\tau_S+b_k\tau_A,\qquad
C(k,j)=n_k\tau_Sp_S+b_k\tau_Ap_A.
\]

Deriving the two attempt processes requires tracking their counter/stage histories and activation/deactivation, not just fitting the two observed collision percentages. These equations describe a proposed extension, **not an implemented or validated replacement** for the current transient closure. Even the homogeneous simulator can produce aggregate role differences through state/history selection; measured unconditional role ratios alone do not identify a state-conditional mechanism.
