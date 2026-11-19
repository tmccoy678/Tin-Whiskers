# Swiss open-silicon comparison: Occamy, MemPool, and adaptive material

## Representative systems

**Occamy** is the principal contemporary reference. ETH Zürich and the
University of Bologna's PULP team fabricated a dual-chiplet, dual-HBM2E,
432-core RISC-V system in GlobalFoundries 12 nm LP+ FinFET on a passive 65 nm
interposer. The 2025 silicon paper reports 768 DP-GFLOP/s peak, 686 GFLOP/s on
dense FP64 GEMM, 571 GFLOP/s on stencil kernels, and 187 GCOMP/s on
sparse-sparse multiplication. Measured energy efficiencies reach 39.8
GFLOP/s/W for dense FP64 and 17.4 GCOMP/s/W for sparse-sparse work. The RTL is
available under a permissive open-source license.

**MemPool** supplies the clean local-memory companion. Its 256 Snitch cores
share a large multi-banked L1 scratchpad through a low-latency interconnect.
The implementation reaches 600 MHz in 22 nm FDX, up to 229 GOPS and 180
GOPS/W, with under 2% execution stalls; an uncontended core reaches shared L1
within five cycles.

Primary sources:

- Scheffler et al. (2025), [Occamy: A 432-Core Dual-Chiplet Dual-HBM2E
  768-DP-GFLOP/s RISC-V System](https://arxiv.org/abs/2501.07330).
- Riedel et al. (2023), [MemPool: A Scalable Manycore Architecture with a
  Low-Latency Shared L1 Memory](https://arxiv.org/abs/2303.17742).

## Exact architectural comparison

| Dimension | Swiss open silicon | Adaptive material screen | Productive shared question |
|---|---|---|---|
| Throughput | Occamy: 686 dense FP64 GFLOP/s, 571 stencil GFLOP/s, 187 sparse GCOMP/s. MemPool: 229 GOPS. | 9,748 adaptive choices/s; 3.74 million persistent field writes/s; 1.72 million growth-candidate evaluations/s. | Report compute operations and adaptive transitions as distinct rates, then measure useful transport or repair gained per joule and per second. |
| Energy | Occamy: up to 39.8 GFLOP/s/W dense and 17.4 GCOMP/s/W sparse-sparse. MemPool: 180 GOPS/W. | Current evidence establishes throughput, work density, and 24.2 MB/s causal audit. | Measure Studio package joules/choice, then physical-medium joules per topology change, delivered charge, and recovered service. |
| Process and body | Two 73 mm² 12 nm chiplets, 65 nm passive interposer, 32 GiB HBM2E, 432 cores. | Present screen: 16 × 8 five-field body. Physical candidates: aqueous PEDOT:PSS microcell and capped Ag/Ge-Se conductive bridge. | Sweep spatial scale while retaining the same task, consequence, energy, material, and damage measures. |
| Local memory | Occamy cluster: 128 KiB, 32-bank SPM shared by eight workers and one DMA core. MemPool: shared multi-banked L1 across 256 cores. | Conductance, electric field, concentration, reservoir, and heat persist locally in each body. | Test whether topology-local state reduces explicit state transfer while preserving service and adaptation. |
| Data movement | Per-cluster 512-bit DMA moves up to 64 B/cycle; double-buffered tiles overlap HBM/chiplet transfer with compute. Each Occamy chiplet exposes 381.47 GiB/s aggregate HBM-controller bandwidth. | Each choice advances the local fields and writes a 2.48 KB causal record; present implementation preserves every choice. | Compare full audit, compact sufficient-state audit, and material-local memory to quantify evidence value per transported byte. |
| Parallelism | Occamy: 48 clusters and 432 compute cores; MemPool: 256 independently executing cores. | 14,400 seed/environment bodies are independent and currently execute through one process/core. | Batch bodies across Studio cores and measure scaling efficiency, choices/s, energy/choice, and seed-level repeatability. |
| Irregular access | Occamy's stream units generate strided and indirect accesses, intersections, and unions in hardware, reaching 42–83% FPU utilization on sparse/stencil work. | Field-weighted candidate selection follows changing local consequences and concealed perturbations. | Apply the same sparse gather, stencil, and graph-routing demands to fixed and adaptive topologies. |
| Fault handling | Occamy calibrates 38 D2D PHYs, disables faulty lanes, and reshuffles packets across the functioning set with linear bandwidth degradation. Groups can be clock-gated, reset, and isolated. | The controller detects consequence change, enters balanced renewal, and maintains finite material and reinforcement ledgers; separate cut experiments demonstrate reconnection. | Use Occamy's lane-disable curve as the fixed remapping control and measure adaptive recovery time, retained bandwidth, material, and energy under identical lesions. |
| Openness | RISC-V ISA, open PULP components, permissively available Occamy RTL and toolchain extensions. | Private reproducible Rust controller, frozen manifests, exact seeds, complete audit, and permissive project direction. | Publish mature benchmark schemas and controls so digital and material implementations can run the same tasks. |

## What Occamy teaches the adaptive body

1. **Hierarchy earns efficiency.** Occamy keeps fine-grained work in local
   128 KiB SPMs, joins four clusters into groups, and uses HBM only through
   explicit tiled movement. The material analogue is a hierarchy of local
   receptive branches, transport trunks, and sparse long-range bridges.
2. **Movement can overlap transformation.** Occamy's DMA fills one tile while
   cores consume another. A growing substrate can similarly maintain one route
   while another branch samples, widens, repairs, or prepares the next demand.
3. **Sparse structure deserves native machinery.** Occamy's stream units turn
   indirection, intersection, and union into hardware operations. The adaptive
   body already treats local field consequences as native selection signals;
   graph intersection and alternate-route recruitment are the next useful
   tasks.
4. **Graceful degradation is measurable.** Occamy's D2D allocator converts
   disabled PHYs into a linear bandwidth curve. This gives the adaptive medium
   an excellent fixed control: equal initial transport, identical lane cuts,
   then compare remapping with remodeling and regrowth.
5. **Instrumentation belongs inside the architecture.** Occamy has 16
   retargetable performance counters per cluster and measured power domains.
   The material body can mirror this with local field, current, heat, material,
   and repair counters retained at the smallest sufficient resolution.

## Positive opportunities for our system

- **Continuous consequence response:** the adaptive controller can change its
  selection after the environment changes; Occamy supplies a strong fixed
  programmable baseline for the same demand.
- **Topology as memory:** present conductance and reservoir fields already
  influence later action and service. Measuring avoided external bytes per
  retained function turns that behavior into a memory result.
- **Repair as communication:** Occamy preserves communication by reallocating
  healthy lanes; the material program can add widening and regrowth, then
  quantify the service recovered per unit time, energy, and matter.
- **Embarrassingly parallel development:** the current 14,400 independent
  bodies map naturally onto Studio cores today and PULP-like many-core workers
  later. The observed 0.22% two-seed throughput range supplies a strong base for
  parallel scaling.
- **Slow adaptive plane, fast compute plane:** at 9,748 choices/s, one reduced
  adaptive choice occupies about 103 µs. That timescale can manage topology,
  routing, repair, and sensing while a conventional many-core performs the
  high-rate arithmetic.

## Smallest decisive joint benchmark

1. Create a fixed hierarchical fabric modeled on Occamy's local SPM → group →
   chiplet structure and an equal-material adaptive fabric.
2. Drive both with the same sparse gather and stencil traffic, energy budget,
   terminals, local memory, and offered load.
3. Disable an identical fraction of long-range links using Occamy's linear
   lane-loss experiment as the fixed remapping control.
4. Continue the adaptive loop with the same finite material and control-energy
   budgets.
5. Measure delivered traffic, p95 latency, bytes moved, joules, peak local
   current/heat, repair time, retained service, and material recruited.

Every gain—higher retained traffic, fewer transported bytes, lower energy,
faster recovery, stronger graceful degradation, or improved work per adaptive
choice—becomes the next scale and lesion test.
