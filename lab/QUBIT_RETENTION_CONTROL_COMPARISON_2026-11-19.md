# Five physical routes to retaining quantum state

These five modalities occupy complementary retention niches. Superconducting
circuits convert microsecond-scale physical lifetime into fast gates and rapid
error-correction cycles. Trapped ions and neutral atoms place millions of
operation intervals inside measured coherence windows. Silicon spins combine
semiconductor-scale geometry with seconds-scale energy retention and
millisecond-scale echo coherence. Photonic systems retain information through
controlled propagation, so lifetime becomes a path-loss and delay budget.

Representative values below come from current system specifications and
peer-reviewed measurements. They define measured operating envelopes rather
than a single rank.

| Physical approach | Representative retention | Representative operation time | Environment and physical scale | Error strategy | Connectivity / movement | What losing the state means |
|---|---|---|---|---|---|---|
| Superconducting circuit | Willow mean `T1 = 68 ± 13 µs`; specialized transmons report median `T1 = 425 µs` and median echo `T2 = 541 µs` | Gates span tens to hundreds of ns; Willow surface-code cycle `1.1 µs` | Lithographic circuits with roughly `100 µm`–mm features in a dilution refrigerator near `10–20 mK` | Surface code, repeated syndrome extraction, real-time decoding, reset, and leakage removal | Fixed 2D nearest-neighbour couplers; Willow average connectivity `3.47` | Energy relaxation, phase randomization, or leakage into higher transmon levels |
| Trapped ion | Hyperfine-clock-state demonstration `T2* = 50 s`; H2 typical memory error `2 × 10^-4` per average depth-1 circuit | Routine gates occupy few-to-tens of µs; specialized entangling gates reach `480 ns` | Individual ions in ultrahigh vacuum with laser-cooled motion and µm–`100 µm` separations | Mid-circuit measurement, qubit reuse, logical codes, and sympathetic/repeated cooling | QCCD transport supplies all-to-all logical connectivity; H2 has four gate zones | Internal-state dephasing or decay, motional heating, leakage, or physical ion loss |
| Neutral atom | Echo `T2 = 7.4 s` for alkali atoms and `40 s` for alkaline-earth atoms | Rydberg operations around `1 µs` | µK atoms in optical tweezers, typically separated by a few µm | Surface-, colour-, and LDPC-style codes, erasure conversion, atom-loss detection, and replacement | Dynamic 2D atom transport; a logical processor used up to 280 atoms | Ground-state dephasing, Rydberg decay, or atom loss; detected loss becomes a located erasure |
| Silicon spin | Foundry devices report `T1 = 9.5 s`, `T2* = 40.6 µs`, and Hahn `T2 = 1.9 ms` | Rabi control up to `5 MHz` gives approximately `0.1 µs` single-spin rotations; exchange operations span ns–µs | Gate-defined quantum dots at tens-of-nm scale in mK dilution refrigerators | Dynamical decoupling, isotopic purification, surface-code layouts, and leakage/valley management | Primarily nearest-neighbour exchange; shuttling and photonic links extend reach | Spin relaxation, phase diffusion from magnetic or charge noise, valley/charge leakage, or loss of the confined electron |
| Photonic / time-bin | A `253.286 m` fibre delay retains a time bin for `1.239 µs`; longer storage follows fibre length and multiplicative transmission | Aurora uses a `1 MHz` quantum clock and approximately `976 ns` measurement-to-feedforward path | µm-scale waveguides, mm chips, and metre–km fibres; room-temperature optical paths with cryogenic photon detectors | Heralded erasure, multiplexing, fusion/cluster states, GKP/bosonic encoding, and loss-budgeted fault tolerance | Photons provide native movement and remote interference through chips and fibre | Absorption, scattering, failed coupling or detection, mode mismatch, or phase/polarization drift; photon loss often becomes a located erasure |

## Measured positive leads

- **Retention-to-operation opportunity:** trapped ions and neutral atoms reach
  approximately `10^6–10^7` gate-time intervals inside demonstrated coherence
  windows.
- **Correction rhythm:** superconducting circuits execute a measured `1.1 µs`
  surface-code cycle and demonstrate below-threshold logical-memory scaling.
- **Integration density:** silicon spins combine nanometre device geometry with
  seconds-scale `T1`.
- **Native movement:** photons and transported atoms or ions make information
  routing a physical operation rather than fixed-wire adjacency.
- **Informative loss:** neutral atoms and photons can convert disappearance into
  a known-location erasure that contributes directly to decoding.

## Primary and authoritative anchors

- Google Quantum AI. [Willow system metrics](https://quantumai.google/static/site-assets/downloads/willow-spec-sheet.pdf)
  and [below-threshold surface-code memory](https://www.nature.com/articles/s41586-024-08449-y).
- Sunada et al. [Near-millisecond energy relaxation and dephasing in a transmon](https://www.nature.com/articles/s41467-025-61126-0).
- Quantinuum. [System Model H2 product data sheet](https://docs.quantinuum.com/h-series/data_sheets/Quantinuum%20H2%20Product%20Data%20Sheet.pdf).
- Harty et al. [Fifty-second trapped-ion memory coherence](https://arxiv.org/abs/1403.1524)
  and Schäfer et al. [sub-microsecond trapped-ion entangling gates](https://arxiv.org/abs/1709.06952).
- Bluvstein et al. [Logical processor with reconfigurable neutral-atom arrays](https://www.nature.com/articles/s41586-023-06927-3)
  and Covey et al. [neutral-atom processing-node coherence and gate envelope](https://www.nature.com/articles/s41534-023-00759-9).
- Camenzind et al. [Industry-compatible silicon spin-qubit unit cells](https://www.nature.com/articles/s41586-025-09531-9.pdf).
- Thomas et al. [Modular photonic architecture, fibre delay, and feedforward system](https://www.nature.com/articles/s41586-024-08406-9).
