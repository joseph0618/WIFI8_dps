# DPS threshold sensitivity

Uniform integer payload range, not a universal ns-3 distribution. Strict payload > threshold rule; identical per-STA arrival/size streams across policies.

Payload range: [64, 1500] bytes, inclusive integer uniform. 10 s/run, 3 seeds.
Zero threshold routes all packets through DPS; threshold >= largest payload reduces to direct LC DCF.
Only delivered packets enter delay and per-delivery metrics. Saturated runs are capacity tests, not equal offered-byte-rate tests.
A threshold that looks best here is workload-dependent; no universal optimal threshold is claimed.

| Traffic | STAs | Model | Threshold bytes | Mbps | Delay ms | W/STA | J/Mbit | DPS fraction |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| saturated | 5 | bianchi |  | 0.7596 | 40.586 | 0.2541 | 1.6726 | 0.0000 |
| saturated | 5 | bianchi_hc |  | 4.4229 | 7.052 | 0.4986 | 0.5636 | 0.0000 |
| saturated | 5 | dps | 0 | 1.9681 | 15.842 | 0.2157 | 0.5480 | 1.0000 |
| saturated | 5 | dps | 256 | 1.9947 | 15.643 | 0.2210 | 0.5539 | 0.8641 |
| saturated | 5 | dps | 512 | 1.8251 | 17.052 | 0.2298 | 0.6297 | 0.6849 |
| saturated | 5 | dps | 1024 | 1.1980 | 25.874 | 0.2461 | 1.0272 | 0.3307 |
| saturated | 5 | dps | 1500 | 0.7596 | 40.586 | 0.2541 | 1.6726 | 0.0000 |
| saturated | 20 | bianchi |  | 0.6307 | 175.325 | 0.2132 | 6.7619 | 0.0000 |
| saturated | 20 | bianchi_hc |  | 4.1355 | 29.912 | 0.4720 | 2.2825 | 0.0000 |
| saturated | 20 | dps | 0 | 1.9646 | 63.243 | 0.1702 | 1.7326 | 1.0000 |
| saturated | 20 | dps | 256 | 1.9758 | 62.791 | 0.1746 | 1.7679 | 0.8663 |
| saturated | 20 | dps | 512 | 1.8010 | 68.783 | 0.1843 | 2.0464 | 0.6817 |
| saturated | 20 | dps | 1024 | 1.1501 | 105.991 | 0.2031 | 3.5339 | 0.3186 |
| saturated | 20 | dps | 1500 | 0.6307 | 175.325 | 0.2132 | 6.7619 | 0.0000 |
| saturated | 50 | bianchi |  | 0.5133 | 474.696 | 0.2046 | 19.9395 | 0.0000 |
| saturated | 50 | bianchi_hc |  | 3.6781 | 81.692 | 0.4666 | 6.3433 | 0.0000 |
| saturated | 50 | dps | 0 | 1.9660 | 157.877 | 0.1612 | 4.0985 | 1.0000 |
| saturated | 50 | dps | 256 | 1.9815 | 156.261 | 0.1657 | 4.1802 | 0.8634 |
| saturated | 50 | dps | 512 | 1.7976 | 170.710 | 0.1753 | 4.8761 | 0.6809 |
| saturated | 50 | dps | 1024 | 1.1265 | 262.574 | 0.1941 | 8.6182 | 0.3149 |
| saturated | 50 | dps | 1500 | 0.5133 | 474.696 | 0.2046 | 19.9395 | 0.0000 |
| poisson | 5 | bianchi |  | 0.1570 | 8.953 | 0.1276 | 4.0721 | 0.0000 |
| poisson | 5 | bianchi_hc |  | 0.1570 | 1.710 | 0.3063 | 9.7809 | 0.0000 |
| poisson | 5 | dps | 0 | 0.1570 | 3.797 | 0.1093 | 3.4901 | 1.0000 |
| poisson | 5 | dps | 256 | 0.1570 | 3.750 | 0.1095 | 3.4974 | 0.8558 |
| poisson | 5 | dps | 512 | 0.1570 | 4.001 | 0.1110 | 3.5436 | 0.6704 |
| poisson | 5 | dps | 1024 | 0.1570 | 5.877 | 0.1179 | 3.7636 | 0.2919 |
| poisson | 5 | dps | 1500 | 0.1570 | 8.953 | 0.1276 | 4.0721 | 0.0000 |
| poisson | 20 | bianchi |  | 0.6292 | 64.904 | 0.1880 | 5.9766 | 0.0000 |
| poisson | 20 | bianchi_hc |  | 0.6309 | 1.899 | 0.3200 | 10.1478 | 0.0000 |
| poisson | 20 | dps | 0 | 0.6301 | 4.635 | 0.1223 | 3.8816 | 1.0000 |
| poisson | 20 | dps | 256 | 0.6301 | 4.591 | 0.1232 | 3.9109 | 0.8725 |
| poisson | 20 | dps | 512 | 0.6301 | 5.061 | 0.1279 | 4.0603 | 0.6881 |
| poisson | 20 | dps | 1024 | 0.6292 | 9.126 | 0.1492 | 4.7436 | 0.3223 |
| poisson | 20 | dps | 1500 | 0.6292 | 64.904 | 0.1880 | 5.9766 | 0.0000 |
| poisson | 50 | bianchi |  | 0.5288 | 2748.273 | 0.2043 | 19.3237 | 0.0000 |
| poisson | 50 | bianchi_hc |  | 1.5523 | 2.269 | 0.3470 | 11.1786 | 0.0000 |
| poisson | 50 | dps | 0 | 1.5516 | 11.756 | 0.1479 | 4.7678 | 1.0000 |
| poisson | 50 | dps | 256 | 1.5516 | 11.164 | 0.1507 | 4.8574 | 0.8652 |
| poisson | 50 | dps | 512 | 1.5512 | 18.886 | 0.1634 | 5.2679 | 0.6846 |
| poisson | 50 | dps | 1024 | 1.1301 | 1234.105 | 0.1937 | 8.5723 | 0.3136 |
| poisson | 50 | dps | 1500 | 0.5288 | 2748.273 | 0.2043 | 19.3237 | 0.0000 |
