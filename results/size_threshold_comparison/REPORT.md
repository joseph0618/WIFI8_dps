# Experiment results

Uniform integer payload sizes from 64 through 1500 bytes, inclusive; each byte size has probability 1/1437. Independent draw per generated packet.
DPS rule: head payload > 512 bytes uses EBSR then AP ICF/ICR/DATA/ACK on HC; smaller/equal payloads use direct LC DATA/ACK.
Models remain named bianchi (LC), dps (size-triggered), and bianchi_hc (HC).
This is a synthetic size-based policy, not a validated claim of real deployment behavior.
ns-3 has application-dependent traffic: [OnOff uses a configurable fixed packet size](https://www.nsnam.org/doxygen/db/d5c/classns3_1_1_on_off_application.html); [application-specific generators differ](https://www.nsnam.org/docs/models/html/applications.html). This uniform workload is not an ns-3 default.
Jain fairness uses delivered packet counts per STA; it is not byte-throughput fairness when payload sizes vary.
Size/arrival random streams are shared across models by seed. Saturated models deliver different prefixes; Poisson queue overflow may retain different packets.
Throughput uses actual delivered payload bits. EBSR-to-HC-UL mean uses only completed DPS grants, excluding direct LC deliveries.
Packet PRR and mean delay may hide packet-size selection effects; byte PRR and energy/Mbit are provided below.

All power, rates and transition delays are research assumptions; see config.json.
Error bars are one standard error. Delivered delay excludes undelivered packets.

| Traffic | Model | STAs | Mbps | Delay ms | PRR | W/STA | mJ/packet |
|---|---|---:|---:|---:|---:|---:|---:|
| saturated | bianchi | 5 | 0.7596 | 40.586 | 0.9959 | 0.2541 | 10.343 |
| saturated | bianchi | 10 | 0.7020 | 86.141 | 0.9913 | 0.2273 | 20.040 |
| saturated | bianchi | 15 | 0.6579 | 138.718 | 0.9859 | 0.2184 | 31.191 |
| saturated | bianchi | 20 | 0.6307 | 175.325 | 0.9806 | 0.2132 | 42.114 |
| saturated | bianchi | 30 | 0.5849 | 283.845 | 0.9688 | 0.2085 | 67.176 |
| saturated | bianchi | 50 | 0.5133 | 474.696 | 0.9422 | 0.2046 | 125.441 |
| saturated | dps | 5 | 1.8251 | 17.052 | 0.9983 | 0.2298 | 3.923 |
| saturated | dps | 10 | 1.8145 | 34.281 | 0.9966 | 0.1997 | 6.861 |
| saturated | dps | 15 | 1.8242 | 51.293 | 0.9949 | 0.1893 | 9.746 |
| saturated | dps | 20 | 1.8010 | 68.783 | 0.9931 | 0.1843 | 12.730 |
| saturated | dps | 30 | 1.8125 | 102.444 | 0.9898 | 0.1795 | 18.532 |
| saturated | dps | 50 | 1.7976 | 170.710 | 0.9830 | 0.1753 | 30.327 |
| saturated | bianchi_hc | 5 | 4.4229 | 7.052 | 0.9993 | 0.4986 | 3.518 |
| saturated | bianchi_hc | 10 | 4.3679 | 14.229 | 0.9986 | 0.4820 | 6.889 |
| saturated | bianchi_hc | 15 | 4.2492 | 21.971 | 0.9978 | 0.4759 | 10.544 |
| saturated | bianchi_hc | 20 | 4.1355 | 29.912 | 0.9970 | 0.4720 | 14.257 |
| saturated | bianchi_hc | 30 | 3.9924 | 46.227 | 0.9953 | 0.4694 | 22.102 |
| saturated | bianchi_hc | 50 | 3.6781 | 81.692 | 0.9916 | 0.4666 | 39.619 |
| poisson | bianchi | 5 | 0.1570 | 8.953 | 0.9988 | 0.1276 | 24.549 |
| poisson | bianchi | 10 | 0.3253 | 11.405 | 0.9981 | 0.1469 | 28.040 |
| poisson | bianchi | 15 | 0.4859 | 15.818 | 0.9974 | 0.1655 | 31.781 |
| poisson | bianchi | 20 | 0.6292 | 64.904 | 0.9974 | 0.1880 | 37.194 |
| poisson | bianchi | 30 | 0.5988 | 1483.524 | 0.6307 | 0.2078 | 65.585 |
| poisson | bianchi | 50 | 0.5288 | 2748.273 | 0.3335 | 0.2043 | 123.018 |
| poisson | dps | 5 | 0.1570 | 4.001 | 0.9988 | 0.1110 | 21.364 |
| poisson | dps | 10 | 0.3254 | 4.366 | 0.9988 | 0.1171 | 22.339 |
| poisson | dps | 15 | 0.4865 | 4.687 | 0.9983 | 0.1229 | 23.587 |
| poisson | dps | 20 | 0.6301 | 5.061 | 0.9984 | 0.1279 | 25.276 |
| poisson | dps | 30 | 0.9392 | 6.254 | 0.9987 | 0.1393 | 27.745 |
| poisson | dps | 50 | 1.5512 | 18.886 | 0.9987 | 0.1634 | 32.847 |
| poisson | bianchi_hc | 5 | 0.1570 | 1.710 | 0.9988 | 0.3063 | 58.972 |
| poisson | bianchi_hc | 10 | 0.3258 | 1.805 | 0.9994 | 0.3112 | 59.336 |
| poisson | bianchi_hc | 15 | 0.4874 | 1.854 | 0.9996 | 0.3159 | 60.547 |
| poisson | bianchi_hc | 20 | 0.6309 | 1.899 | 0.9994 | 0.3200 | 63.192 |
| poisson | bianchi_hc | 30 | 0.9398 | 1.991 | 0.9993 | 0.3290 | 65.499 |
| poisson | bianchi_hc | 50 | 1.5523 | 2.269 | 0.9995 | 0.3470 | 69.696 |

## Size and route statistics

| Traffic | Model | STAs | Mean delivered bytes | Byte PRR | DPS delivery fraction | J/Mbit |
|---|---|---:|---:|---:|---:|---:|
| saturated | bianchi | 5 | 773.02 | 0.9961 | 0.0000 | 1.6726 |
| saturated | bianchi | 10 | 773.26 | 0.9914 | 0.0000 | 3.2389 |
| saturated | bianchi | 15 | 783.12 | 0.9882 | 0.0000 | 4.9791 |
| saturated | bianchi | 20 | 778.54 | 0.9807 | 0.0000 | 6.7619 |
| saturated | bianchi | 30 | 785.31 | 0.9705 | 0.0000 | 10.6928 |
| saturated | bianchi | 50 | 786.37 | 0.9376 | 0.0000 | 19.9395 |
| saturated | dps | 5 | 778.81 | 0.9977 | 0.6849 | 0.6297 |
| saturated | dps | 10 | 779.16 | 0.9961 | 0.6840 | 1.1007 |
| saturated | dps | 15 | 782.45 | 0.9941 | 0.6867 | 1.5570 |
| saturated | dps | 20 | 777.65 | 0.9920 | 0.6817 | 2.0464 |
| saturated | dps | 30 | 779.60 | 0.9878 | 0.6812 | 2.9714 |
| saturated | dps | 50 | 777.43 | 0.9780 | 0.6809 | 4.8761 |
| saturated | bianchi_hc | 5 | 780.28 | 0.9992 | 0.0000 | 0.5636 |
| saturated | bianchi_hc | 10 | 780.39 | 0.9985 | 0.0000 | 1.1034 |
| saturated | bianchi_hc | 15 | 784.45 | 0.9979 | 0.0000 | 1.6801 |
| saturated | bianchi_hc | 20 | 780.79 | 0.9974 | 0.0000 | 2.2825 |
| saturated | bianchi_hc | 30 | 783.28 | 0.9948 | 0.0000 | 3.5271 |
| saturated | bianchi_hc | 50 | 780.76 | 0.9917 | 0.0000 | 6.3433 |
| poisson | bianchi | 5 | 753.26 | 0.9990 | 0.0000 | 4.0721 |
| poisson | bianchi | 10 | 775.78 | 0.9980 | 0.0000 | 4.5179 |
| poisson | bianchi | 15 | 777.86 | 0.9966 | 0.0000 | 5.1076 |
| poisson | bianchi | 20 | 777.78 | 0.9968 | 0.0000 | 5.9766 |
| poisson | bianchi | 30 | 787.23 | 0.6368 | 0.0000 | 10.4128 |
| poisson | bianchi | 50 | 795.86 | 0.3405 | 0.0000 | 19.3237 |
| poisson | dps | 5 | 753.26 | 0.9990 | 0.6704 | 3.5436 |
| poisson | dps | 10 | 775.54 | 0.9984 | 0.6821 | 3.6005 |
| poisson | dps | 15 | 778.06 | 0.9977 | 0.6879 | 3.7899 |
| poisson | dps | 20 | 778.15 | 0.9982 | 0.6881 | 4.0603 |
| poisson | dps | 30 | 779.53 | 0.9987 | 0.6842 | 4.4490 |
| poisson | dps | 50 | 779.43 | 0.9988 | 0.6846 | 5.2679 |
| poisson | bianchi_hc | 5 | 753.26 | 0.9990 | 0.0000 | 9.7809 |
| poisson | bianchi_hc | 10 | 775.98 | 0.9995 | 0.0000 | 9.5580 |
| poisson | bianchi_hc | 15 | 778.58 | 0.9997 | 0.0000 | 9.7221 |
| poisson | bianchi_hc | 20 | 778.39 | 0.9995 | 0.0000 | 10.1478 |
| poisson | bianchi_hc | 30 | 779.56 | 0.9994 | 0.0000 | 10.5025 |
| poisson | bianchi_hc | 50 | 779.37 | 0.9995 | 0.0000 | 11.1786 |
