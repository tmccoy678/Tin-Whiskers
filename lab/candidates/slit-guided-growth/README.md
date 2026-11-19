# Slit-guided conductive growth

This Rust-first candidate asks whether a developing conductor maps coherent
two-aperture interference, maps path-tagged aperture envelopes, and preserves
an earlier wave history after the optical condition changes.

Two sparse optical apertures provide the field. Conductive material grows by
four-neighbour recruitment on a `192 × 128` lattice; every condition receives
the same source, barrier, slit geometry, wavelength, step budget, and seed
ensemble. Four histories are compared:

1. coherent throughout;
2. path-tagged throughout, represented by orthogonal/incoherent aperture
   intensities with the cross term removed;
3. coherent then path-tagged at step 6,000;
4. path-tagged then coherent at step 6,000.

The optical field is a scalar Huygens/Fresnel screening model. It provides a
classical field-and-history test and a direct precursor to single-photon event
sampling, polarization tagging, and Maxwell/FDTD verification.

## Result

| Field history | Connected / 32 | Wilson 95% interval | Median connection step |
|---|---:|---:|---:|
| Coherent throughout | **26 / 32** | `[0.647, 0.911]` | **10,190.5** |
| Path-tagged throughout | **0 / 32** | `[0.000, 0.107]` | — |
| Coherent → path-tagged at 6,000 | **0 / 32** | `[0.000, 0.107]` | — |
| Path-tagged → coherent at 6,000 | **32 / 32** | `[0.893, 1.000]` | **10,958.5** |

The coherent and path-tagged connection rates separate strongly in the matched
ensemble (Fisher exact `p = 3.01 × 10^-12`). Switch direction is stronger still
(`p = 1.09 × 10^-18`): turning coherence on at the midpoint restored connection
for every seed, while the material grown before the switch remained part of the
later body. Coherent conditions also produced higher coherent-field alignment
and greater forward reach at intermediate budgets.

This is the central positive result: present optical coherence and accumulated
material history jointly determine whether an equal material budget completes
a conductive route.

## Visual evidence

The two-chapter movie overlays the exact optical intensity and occupied-cell
anatomy. Chapter one compares coherent and path-tagged growth; chapter two
compares both switch directions and holds the field change at step 6,000.

[Open the slit-guided growth movie](../../../figures/slit-guided-conductive-growth.mp4)

## Application direction

Sparse optical fibres can act as stimulation/readout trunks while the
conductive material supplies distributed local anatomy. A high-reliability
medical-device path begins with a confined self-repairing interconnect inside a
hermetic pacemaker package or lead: repeated microcracks become controlled
lesions, a conventional route supplies the fixed safety control, and the
adaptive medium is scored on restored capture, heat, energy, repair time, and
lifetime.

## Earth-lab mapping

- [`../../EARTH_SLIT_GUIDED_MEDIUM_2026-11-19.md`](../../EARTH_SLIT_GUIDED_MEDIUM_2026-11-19.md)
  selects a 450 nm photoelectrochemical PEDOT/hematite/FTO medium, two sparse
  fibre channels, finite 80 nmol EDOT reservoir, bounded three-electrode drive,
  and six-chip paired falsifier.
- [`../../SLIT_GUIDED_EARTH_DIMENSIONING_2026-11-19.md`](../../SLIT_GUIDED_EARTH_DIMENSIONING_2026-11-19.md)
  maps the `192 × 128` field to a `288 × 192 µm` growth plane with `13.5 µm`
  apertures, `48 µm` centres, `232.5 µm` downstream distance, and a Maxwell/FDTD
  admission test.
- [`../../RUST_FIRST_VALIDATION_ARCHITECTURE_2026-11-19.md`](../../RUST_FIRST_VALIDATION_ARCHITECTURE_2026-11-19.md)
  defines the unified Rust field/growth/conduction/audit instrument and frozen
  MOOSE cross-check.

Run:

```sh
cargo run --release -- output
```

The output contains coherent and path-tagged field maps, 32-seed metrics for
each condition, and exact seed-319 occupied-cell frames.

## Integrity

| Artifact | SHA-256 |
|---|---|
| `metrics.tsv` | `cfc95e8cb9fa40ffe4267ad02b6a7cc5bc550a6e546f0853b936fdf539690fef` |
| `coherent-field.pgm` | `07bd4a58e9f1348ee1d9f81e85190a45083a233d84360959f3147e8f446388ff` |
| `path-tagged-field.pgm` | `d124a3a1fe6e4438f1f4bb40f5745b244adce995f1ffa4c5eeb63f6c2d58bc1d` |
| H.264 movie | `1830c4269e34480f51dc27e4c89bd33435ce2341d9a539ad5ada161ec213289a` |
