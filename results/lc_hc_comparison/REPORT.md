# Experiment results

All power, rates and transition delays are research assumptions; see config.json.
Error bars are one standard error. Delivered delay excludes undelivered packets.

| Traffic | Model | STAs | Mbps | Delay ms | PRR | W/STA | mJ/packet |
|---|---|---:|---:|---:|---:|---:|---:|
| saturated | bianchi | 5 | 0.8108 | 50.207 | 0.9950 | 0.2575 | 12.998 |
| saturated | bianchi | 10 | 0.7581 | 102.671 | 0.9893 | 0.2300 | 24.836 |
| saturated | bianchi | 15 | 0.7156 | 162.254 | 0.9831 | 0.2206 | 37.847 |
| saturated | bianchi | 20 | 0.6896 | 209.913 | 0.9768 | 0.2153 | 51.097 |
| saturated | bianchi | 30 | 0.6514 | 314.032 | 0.9637 | 0.2101 | 79.180 |
| saturated | bianchi | 50 | 0.5846 | 516.163 | 0.9346 | 0.2059 | 144.116 |
| saturated | dps | 5 | 2.4309 | 16.822 | 0.9983 | 0.2240 | 3.771 |
| saturated | dps | 10 | 2.4298 | 33.626 | 0.9966 | 0.1908 | 6.426 |
| saturated | dps | 15 | 2.4282 | 50.442 | 0.9950 | 0.1797 | 9.084 |
| saturated | dps | 20 | 2.4293 | 67.163 | 0.9933 | 0.1742 | 11.738 |
| saturated | dps | 30 | 2.4287 | 100.594 | 0.9900 | 0.1687 | 17.055 |
| saturated | dps | 50 | 2.4230 | 167.459 | 0.9834 | 0.1643 | 27.740 |
| saturated | bianchi_hc | 5 | 5.0973 | 8.017 | 0.9992 | 0.5135 | 4.122 |
| saturated | bianchi_hc | 10 | 5.0479 | 16.112 | 0.9984 | 0.4924 | 7.984 |
| saturated | bianchi_hc | 15 | 4.9164 | 24.615 | 0.9975 | 0.4846 | 12.101 |
| saturated | bianchi_hc | 20 | 4.8048 | 33.597 | 0.9966 | 0.4798 | 16.344 |
| saturated | bianchi_hc | 30 | 4.6641 | 51.640 | 0.9948 | 0.4759 | 25.049 |
| saturated | bianchi_hc | 50 | 4.3591 | 90.172 | 0.9907 | 0.4719 | 44.303 |
| poisson | bianchi | 5 | 0.2043 | 11.054 | 0.9974 | 0.1351 | 27.058 |
| poisson | bianchi | 10 | 0.4174 | 14.278 | 0.9993 | 0.1587 | 31.144 |
| poisson | bianchi | 15 | 0.6296 | 29.210 | 0.9991 | 0.1843 | 35.972 |
| poisson | bianchi | 20 | 0.7243 | 532.180 | 0.8824 | 0.2127 | 48.074 |
| poisson | bianchi | 30 | 0.6547 | 1913.149 | 0.5337 | 0.2098 | 78.699 |
| poisson | bianchi | 50 | 0.6053 | 2834.336 | 0.2963 | 0.2057 | 139.039 |
| poisson | dps | 5 | 0.2049 | 3.955 | 1.0000 | 0.1103 | 22.045 |
| poisson | dps | 10 | 0.4177 | 4.231 | 1.0000 | 0.1154 | 22.644 |
| poisson | dps | 15 | 0.6296 | 4.572 | 0.9987 | 0.1204 | 23.547 |
| poisson | dps | 20 | 0.8225 | 4.942 | 0.9990 | 0.1249 | 24.897 |
| poisson | dps | 30 | 1.2279 | 6.172 | 1.0000 | 0.1344 | 26.898 |
| poisson | dps | 50 | 2.0345 | 16.656 | 0.9957 | 0.1536 | 30.905 |
| poisson | bianchi_hc | 5 | 0.2049 | 1.918 | 1.0000 | 0.3077 | 61.466 |
| poisson | bianchi_hc | 10 | 0.4177 | 2.021 | 1.0000 | 0.3134 | 61.490 |
| poisson | bianchi_hc | 15 | 0.6302 | 2.063 | 0.9995 | 0.3192 | 62.364 |
| poisson | bianchi_hc | 20 | 0.8228 | 2.130 | 0.9997 | 0.3243 | 64.662 |
| poisson | bianchi_hc | 30 | 1.2279 | 2.267 | 1.0000 | 0.3353 | 67.117 |
| poisson | bianchi_hc | 50 | 2.0422 | 2.658 | 0.9995 | 0.3575 | 71.658 |
