# Field and dissipation result

MOOSE computed voltage gradients, current-density proxy, and Joule density on the same finite-element state used for terminal flux. The Joule integral agrees with boundary power at one normalized volt.

| Topology | Joule at ΔV=1 | Peak current density | Voltage for straight-wire current | Joule at straight-wire current |
|---|---:|---:|---:|---:|
| Straight wire | 0.015853 | 1.083779 | 1.000 | 0.015853 |
| Parallel grid | 0.079262 | 1.083781 | 0.200 | 0.003171 |
| Grown Cherenkov | 0.003470 | 1.123181 | 3.834 | 0.051000 |
| Recurrently developed | 0.003475 | 1.111673 | 3.874 | 0.052144 |

At equal voltage, both grown topologies dissipate less total power because they carry less current. Their local peak current-density proxies remain slightly above the wire and grid. At equal delivered current, the grown topologies require higher voltage and dissipate more power. Low total flux therefore identifies a low-power state, not uniformly low local electrical stress.
