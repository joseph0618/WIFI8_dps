# Bianchi、全 LC UL 存取與 LC/HC DPS 的數學分析

本文對應本資料夾的研究模擬。目標是推導 throughput、delay 與 energy 的改善條件，區分存取機制、資料速率與動態 capability 切換的收益。以下精確時間帳本、解析近似與未實作擴充會分別標示；不是 IEEE 802.11bn 標準符合性證明。

## 1. Current model names

This appendix retains background derivations, including hypothetical all-LC comparisons. The current executable models are `bianchi` (LC DCF), `dps` (LC contention with HC service), and `bianchi_hc` (HC DCF). The all-LC DPS implementation has been removed.

DPS uses two contentions: the STA wins a TXOP for EBSR, then the AP wins a separate TXOP for ICF–ICR–DATA–ACK. Comparing DPS with LC DCF combines access and data-rate effects; comparing DPS with HC DCF also changes access behavior. Neither comparison isolates capability switching alone.

See [the current derivation](../MATHEMATICAL_ANALYSIS.md) and [metric definitions](../README.md) for the collision ratio and paired EBSR-to-HC-UL attempt count. Historical time-rate formulas below are background, not current plotted metrics.
## 2. 模型假設與參數

單一共享通道、無 hidden node、無 capture、無 PHY errors。其他 backoff 在忙碌期間凍結。初始 backoff 均勻取 0…W−1；碰撞後 stage 增加，上限 m，CW 選項數為 W·2^stage。沒有 retry limit。AP 使用相同 W、m。

每個 EBSR 對應一台 STA 的一個待服務封包；該 STA 等 AP 期間不再競爭。AP FIFO，一次 TXOP 只服務一包；沒有 aggregation 或多使用者並行。EBSR 不額外 ACK。這些是研究假設，不是對真實 DPS 所有操作的宣稱。

HC 流程：EBSR(LC) → AP 競爭 → ICF(LC) → SIFS+propagation → SWITCH_UP → ICR(HC) → DATA(HC) → ACK(HC) → SWITCH_DOWN → propagation+DIFS。ICR/ACK 的控制速率仍為 R_C，HC 不等於所有控制 frame 都加速。只被服務的 STA 升 HC，AP 能耗不計；其餘 STA 保持 LC。

升降期間保留通道，其他節點不能競爭；切換與間隔不重疊。這是保守的序列化假設，沒有實作標準 padding overlap 或能力矩陣 BW/NSS/MCS；有效 DATA rate 代表 capability 的簡化效果。反向切換在每次 ACK 後進行，沒有 inactivity timer。

| 符號 | 意義 | 預設 |
|---|---|---:|
| N | STA 數量 | 5,10,15,20,30,50 |
| W,m | 初始視窗選項數、最大退避 stage | 32,5 |
| σ,s,d,δ | slot、SIFS、DIFS、單次傳播時間 | 50,28,128,1 μs |
| L,h | payload、DATA 的 PHY+MAC header | 8184,400 bits |
| e,f,r,a | EBSR、ICF、ICR、ACK（含 PHY） | 288,288,240,240 bits |
| R_L,R_H,R_C | LC DATA、HC DATA、control rate | 1,10,1 Mbps |
| u,v | 升 HC、降 LC 延遲 | 100,100 μs |
| λ | 每 STA Poisson arrival rate | 5 packets/s |
| Q | 每 STA queue limit（含待送 head） | 1000 packets |

Mbps=bits/μs。功率預設 LC idle/rx/tx=0.1/0.2/0.5 W；HC idle/rx/tx=0.3/0.5/1 W；switch=0.4 W。所有速率／功率／訊框長度／切換時間都是可調原型假設，不能用預設值證明真實裝置的收益。

## 3. 封包流量與守恆

Saturated 每 STA 在時間 0 有一包；成功 ACK 後立即產生替代包。它表示永遠有資料，不是無限 arrival rate；每 STA outstanding packet 為一，因此 PRR 接近 1 並不意味低 delay。

Poisson：每 STA arrivals 獨立，interarrival X~Exp(λ)。合併 offered load 為 Λ=Nλ packets/s，payload offered bitrate=ΛL。queue 滿則 drop。兩模型使用相同 arrival RNG seed，與 backoff RNG 分開，方便 paired comparison。

固定 observation window T 的守恆式：

\[
G=D+F+Q_{end},\qquad PRR=D/G.
\]

G=generated、D=delivered、F=overflow drops、Q_end=pending。沒有 arrivals 時 PRR 未定義，CSV 為 NaN，不能當成 0 或 1。

## 4. 成功交換與碰撞時間

在 LC Basic，成功交換含 trailing DIFS：

\[
T_B(R)=\frac{h+L}{R}+\frac a{R_C}+s+d+2\delta.
\]

EBSR 成功時間：

\[
T_E=\frac e{R_C}+d+\delta.
\]

AP 觸發的成功交換：

\[
T_U(R)=\frac{f+r+a}{R_C}+\frac{h+L}{R}+3s+d+4\delta.
\]

全 LC 每包兩次成功交換為 T_E+T_U(R_L)。LC/HC 為 T_E+T_U(R_H)+u+v。

Basic 碰撞：T_cB=(h+L)/R_L+d+δ。兩階段流程碰撞為同時發送的 EBSR/ICF 中最長 airtime 加 d+δ。若 e=f，T_cD=e/R_C+d+δ；若長度不同不能始終用單一常數，應分碰撞類型或用碰撞時間總和。

代入預設：T_B(R_L)=8.982 ms，T_E=0.417 ms，T_U(R_L)=9.568 ms；全 LC 固定成功成本=9.985 ms，額外=1.003 ms。T_cB=8.713 ms，T_cD=0.417 ms。

HC 每包兩階段固定成本=0.417+1.8424+0.2=2.4594 ms。常駐 HC Basic 固定成本=1.2564 ms，其碰撞成本=0.9874 ms。不能只用 LC DATA 的 8.584 ms 去估計常駐 HC Basic 碰撞。

## 5. 精確有限時間帳本與長時間 throughput

每段 observation time 只分配一次：

\[
T=T_{idle}+T_{success-path}+T_{collision}.
\]

success-path 包含成功路徑上的 frame、間隔、切換，也包含 horizon 截斷的成功路徑片段，不代表所有該路徑都已完成。collision category 包含碰撞 frame 與後面的 d+δ。idle category 是退避 slot 與沒有 contender 的空閒；不同於 radio idle activity。

在有限時間，精確 throughput=D L/T。只要 D>0，mean_channel_cost=T/D，且 L/mean_channel_cost 恰好等於 throughput。Poisson 低負載時這個成本含沒有需求的閒置，不能將它誤稱 packet access delay。

長時間 saturated 下，定義 I_B、I_D 為每成功 DATA 平均的 idle category 時間，c_B、c_D 為每成功 DATA 的網路碰撞事件數。忽略 horizon 邊界且一包一 EBSR：

\[
C_B=I_B+T_B+c_BT_{cB},
\]
\[
C_D=I_D+T_E+T_U+c_DT_{cD},\qquad S=L/C.
\]

不等长控制 frame 時將 c_D T_cD 改成 T_collision/D。有限時間 EBSR successes 可能大於 delivered，因此 T_success-path 不能直接視為 D(T_E+T_U)。未完成 reports、partial frame 和 idle horizon 都須留在帳本。

改善條件：

\[
\boxed{c_BT_{cB}-c_DT_{cD}>(T_E+T_U-T_B)+(I_D-I_B)}.
\]

左邊是少浪費的碰撞時間；右邊是額外控制與退避。預設單位 ms：8.713c_B−0.417c_D>1.003+I_D−I_B。低 contention 左邊小，兩階段可能輸；高 contention 長 DATA 碰撞成本高，兩階段可能贏。碰撞事件數不一定要下降。

c 是 network collision events/delivered，不能以 collided attempts/attempts 直接替代。多個 STA 同時碰撞，事件只算一次、attempt 可算多次；此外 DPS 每包有兩種競爭成功。

## 6. Bianchi 飽和解析模型

Decoupling 假設：每個節點在虛擬 slot 獨立以 τ 嘗試，遇到 stage-independent conditional collision probability p。W 是選項數，不是最大 counter。

\[
\tau=f(p)=\frac{2}{W+1+Wp\sum_{j=0}^{m-1}(2p)^j},\qquad
p=1-(1-\tau)^{N-1}.
\]

使用 sum 形式避免 p=1/2 的表面奇點。m=0 時 sum 為 0。設 P_0=(1−τ)^N、P_1=Nτ(1−τ)^(N−1)、P_c=1−P_0−P_1：

\[
S_B=\frac{P_1L}{P_0\sigma+P_1T_B+P_cT_{cB}}.
\]

I_B=P_0σ/P_1、c_B=P_c/P_1，與循環帳本一致。τ 是每虛擬 slot 的 transmission probability，不能直接當成 packets/second。模型僅用於 saturated DCF；Poisson 不可直接代入 λ 取代 τ。

程式 bianchi.py 保留原始 saturated simulation 與 analytical_collision_probability/rate。run.py 使用固定時間、有 queue 的模擬作公平 observation-window 比較。解析近似與模擬結果須分開標示。

## 7. 全 LC 兩階段流程的簡化 Markov / semi-Markov 推導

這節是可供後續實作的預測近似，當前模擬並未求解此 chain。

令 k∈{0,…,N} 為已 EBSR、等待 AP 的 STA 數量；saturated 下可競爭 STA 有 n_k=N−k，AP 在 k>0 時活躍。成功 EBSR 使 k→k+1；成功 AP 服務使 k→k−1；idle/collision 留在 k。

定義 τ_s(k)、τ_a(k) 的 conditional attempt probabilities，k=0 時 τ_a=0。可在各 k 內用 decoupling fixed point 近似：

\[
p_s(k)=1-(1-\tau_s(k))^{n_k-1}(1-\tau_a(k)),
\]
\[
p_a(k)=1-(1-\tau_s(k))^{n_k}.
\]

活躍 contender 的 τ≈f(p)。n_k=0 時不計 STA 式；k=0 時不計 AP 式。

\[
P_E(k)=n_k\tau_s(k)(1-\tau_s(k))^{n_k-1}(1-\tau_a(k)),
\]
\[
P_A(k)=\tau_a(k)(1-\tau_s(k))^{n_k},
\]
\[
P_0(k)=(1-\tau_s(k))^{n_k}(1-\tau_a(k)),\quad
P_C(k)=1-P_0(k)-P_E(k)-P_A(k).
\]

n_k=0 時 P_E=0。此 embedded birth-death chain 的 π 是虛擬事件 slot 的穩態機率：

\[
\pi_{k+1}=\pi_k\frac{P_E(k)}{P_A(k+1)},\qquad \sum_k\pi_k=1.
\]

流量守恆給 ΣπP_E=ΣπP_A。因不同事件耗時不同，π 不是 wall-clock occupancy。設：

\[
t(k)=P_0(k)\sigma+P_E(k)T_E+P_A(k)T_U+P_C(k)T_{cD},
\]
\[
\boxed{S_D\approx\frac{L\sum_k\pi_k P_A(k)}{\sum_k\pi_k t(k)}}.
\]

HC 版本將 T_U 改為 T_U(R_H)+u+v；控制碰撞仍在 LC。不同控制長度要分類 P_C 及 duration。

此模型的 k 單獨不是實際 simulator 的精確 Markov state：AP/STA backoff stage 與殘餘 counter 會保留並與 k 相關。用 τ(k)=f(p(k)) 是局部穩態近似，不應聲稱為 exact chain。精確 state 至少包含每 STA queue、report flag、stage、counter、AP stage/counter 與 FIFO grant order；Poisson 還需 arrival/queue 狀態。精確 state space 隨 N、Q 快速膨脹。

## 8. HC 何時值得切換？

只比較同樣的成功存取路徑、相同 frame sizes：

\[
\Delta T_{data}=(h+L)(1/R_L-1/R_H).
\]

忽略 contention distribution 的回饋，HC 單包 airtime 改善條件為：

\[
\boxed{u+v<\Delta T_{data}}.
\]

預設 ΔT_data=7.7256 ms，u+v=0.2 ms，因此固定交換成本降低 7.5256 ms。這不是整體 throughput 增益的完整預測，因到達、queue 與 contender 人數也受時序影響。

若將來一次 TXOP 傳 b 包，切換成本可攤為 (u+v)/b；本版 b=1，尚未實作 aggregation。

## 9. 能耗的精確 reward 積分

對 STA i，記 LC 下 idle/rx/tx 的時間 t_{Li,x}，HC 下 t_{Hi,x}，以及 switch 時間 t_{Si}。全 observation window 必須滿足：

\[
\sum_i\left(\sum_x t_{Li,x}+\sum_x t_{Hi,x}+t_{Si}\right)=NT.
\]

\[
E_{STA}=\sum_i\left(\sum_xP_{L,x}t_{Li,x}+\sum_xP_{H,x}t_{Hi,x}+P_St_{Si}\right).
\]

平均每 STA 功率 E_STA/(NT)；能量／成功包 E_STA/D。後者包含其他 STA overhearing 和整個觀察時間的 idle energy，不是單一傳送 STA 的封包能量。AP 不計。

被傳送 frame 的非 sender STAs 使用 RX power，gap 使用 idle power。LC STA 對 HC DATA 的 RX 在此代表監聽／偵測能耗，不表示能解碼該 DATA；尚未建模 capability-dependent overhearing 或 NAV 睡眠。HC STA 在 switch 時只使用 switch power，不能重複計 HC idle；其他 STA 在該 gap 使用 LC idle。partial frame/switch 在 horizon 截斷，消耗仍計入。

純 DATA 的 tagged transmitter 能耗差為：

\[
\Delta E_{tx}=P_{L,tx}(h+L)/R_L-P_{H,tx}(h+L)/R_H-P_S(u+v).
\]

單位換算 μs→s 後才是 J。此式只是單包 TX 部分；還有 ICR/ACK/SIFS 功率、其他 STA RX 與 queue waiting，不能以 ΔE_tx>0 推出整個網路省電。

循環 reward 方法為 E[E_cycle]/E[T_cycle]。相較常駐 HC，LC 等待時間的潛在收益約為 (P_H,idle−P_L,idle)E[T_wait]，但需計 overhearing RX 差异与控制／切換能量。平均功率與能量／成功包可能呈不同趨勢；不同 delivered load 時比較功率須同時呈報 throughput。

## 10. Delay、Poisson queue 與 PRR

每包 delay=ACK reception time−arrival time；ACK 後 reversion 不算該包 delay，但占用通道、延後下一包。若 ACK 在 T 前完成而降 LC 尚未完成，包仍計 delivered。

\[
D_{packet}=W_q+D_{contention/report}+D_{APwait}+D_{exchange\ to\ ACK}.
\]

平均与 p95 只針對成功包。p95 使用 nearest-rank（排序後第 ceil(0.95D) 包）；summary 的 p95 是各 seed 的 p95 平均，不是把全部 packets 合併的 pooled p95。過載時長等待而未完成的包被排除，因此不能單靠 delivered mean delay 判斷系統健康。

簡單 queue 推論可以把整個網路近似成 M/G/1 virtual server，Λ=Nλ、有效 packet service time X、ρ=ΛE[X]：

\[
E[W_q]\approx\frac{\Lambda E[X^2]}{2(1-\rho)},\quad \rho<1.
\]

但共享 DCF、多 queue、report blocking 使 service 不 iid；此式只用于直觉，不是目前程式精確解析結果。ρ 接近 1 時少量 service-time 改善可能造成巨大 delay 差異。有限 queue 過載時存在 drop，需要 M/G/1/K 或擴充 chain；不能用上式預測 drops。

Stable、低負載、無 PHY errors、長時間 PRR 趨近 1，兩模型 throughput 主要受 offered load 限制，HC 不會凭空增加送來的資料。Overload 下 throughput 受 capacity 限制，PRR 下降可能来自 overflow 或 pending；drop_ratio 與 pending_ratio 應分開報告。

Little's law L_q=λ_eff W_q 要使用相同 population、穩態及 admitted rate；generated rate 不一定等於 admitted/delivered rate。當前輸出未積分 queue occupancy，也未量測 M/G/1 的 E[X²]，因此未宣稱已驗證這兩式。

## 11. 參考 5G BWP 論文如何使用

Ramaswamy、Correia、Swain-Walsh，2021，DOI 10.1109/PIMRC50174.2021.9569671，第 III 節用循環平均分析 bandwidth adaptation，假設每 slot 獨立 Bernoulli grant probability p_g。它不是 Wi-Fi contention model。

在其假設下，連續 K 個無 grant slots 才回 default mode：E[T_active]=Σ_{j=1}^K (1−p_g)^(−j) slots，E[T_default]=1/p_g，E[T_cycle]=k_0+E[T_active]+E[T_default]。其 switching-only scheduling delay 為 k_0/(1+p_gE[T_active])，不是全部 packet delay。

可以借用 reward/cycle 思路，但本版 DPS 每 TXOP 結束回 LC，不是等待 K idle slots；不可直接搬 timer。Poisson 固定物理間隔 Δ 的「至少一 arrival」機率是 1−exp(−λΔ)，不是 collision p，也不是實際 grant probability。Wi-Fi 虛擬 slot 長度不同，更不能直接把 τ 或 λΔ 當論文 p_g。

原論文第 IV 節式 (5) 的 baseline 說明為常駐 active，但印出的功率上標為 d；使用時須核對這個記號不一致，不能不加檢查套用。本專案使用明確 LC/HC watts，沒有直接套用該功率式。

## 12. 數據、統計與如何驗證

執行：

```powershell
python -B run.py --model all --traffic both --duration 30 --runs 5 --output results/lc_hc_comparison
python -B tests/check_models.py
```

results.csv 是每個 seed 的原始全指標；summary.csv 有平均、standard error、valid_runs；comparisons.csv 提供相同 seed 的 candidate−baseline paired differences 與 delta SE。relative_change=100·(candidate_mean−baseline_mean)/baseline_mean，負值對 delay/energy 較好、正值對 throughput 較好。不是每個 seed 百分比的平均。

SE=s/√M，只用有限值；只有一有效 run 時 SE 未定義。誤差棒 ±1 SE 不是 95% CI。若要 95% CI，可用 Student t_{.975,M−1}·SE，須明確假設獨立 seeds、分布近似，並考慮多重比較；本版沒有輸出 CI。

config.json 包含完整 CLI、dataclass parameters、UTC timestamp、source SHA256。REPORT.md 是可讀表格。圖分 traffic_metrics 與 energy_metrics，另有 saturated_metrics／poisson_metrics（delay 使用 symlog 軸）。DATA_DICTIONARY.md 解釋完整欄位。結果依 output 目錄區隔；同目錄重跑覆蓋，舊結果不能混入新 summary。

驗證包括：generated 守恆、radio occupancy=NT、channel ledger=T、LC+HC energy=total、固定相同 watts 的 closed-form integral、HC frame sequence、ACK horizon、HC zero-switch/equal-rate/equal-power 與 LC 精確退化相同。這些證明 implementation consistency，不能代替標準驗證或實測 calibration。

對假設至少掃描 R_H/R_L、u+v、HC/LC power ratio、λ、N；不要只用一組有利 HC 的參數宣稱 DPS 必然較好。先用 saturated 評估 capacity，再用 offered load 從穩定到過載的 Poisson 評估 delay/drop。

## 13. 可報告的結論與限制

1. 全 LC 改善可以來自長 DATA 碰撞改為短控制碰撞，以及 report-waiting 降低活躍競爭 STA 數。
2. 加 HC 的 throughput 改善包含更高 R_H，必須有同速率 baseline。
3. 動態 capability 的省電需足夠 LC 等待時間、合理 power ratio 与 switch costs，並核對 served workload。
4. renewal 時間／能量帳本適合解釋與驗證；獨立預測需求 τ、π 或 service distribution，不能把模擬量出的參數稱為純解析預測。
5. 本版沒有標準 padding、BW/NSS/MCS constraints、PHY errors、aggregation、AP energy、HC inactivity timer、queue occupancy/Little-law validation；它是可調研究模型。

## 14. 來源

- Giuseppe Bianchi, Performance Analysis of the IEEE 802.11 Distributed Coordination Function, IEEE JSAC 18(3), 2000, DOI 10.1109/49.840210。https://www.eng.buffalo.edu/~tmelodia/papers/bianchi.pdf
- V. Ramaswamy, J. T. Correia, D. Swain-Walsh, Analytical Evaluation of Bandwidth Part Adaptation in 5G New Radio, PIMRC 2021, DOI 10.1109/PIMRC50174.2021.9569671。使用者提供的 PDF：C:/Users/User/Downloads/Analytical_Evaluation_of_Bandwidth_Part_Adaptation_in_5G_New_Radio.pdf。
- 程式 src/dps_sim/simulation.py 的數值與行為。本文的兩階段時間帳本、HC 損益與 k-state 擴充為本專案推導，不宣稱上述論文已分析此 DPS 流程。
