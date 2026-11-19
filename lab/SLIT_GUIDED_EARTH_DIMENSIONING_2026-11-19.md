# Earth dimensioning for the 192 × 128 slit-guided screen

## Rust geometry retained

The current model uses a `192 × 128` lattice, a one-cell barrier at `x = 36`,
slit centers at `y = 48` and `80`, inclusive slit width `9` cells, center
separation `32` cells, wavelength `8` cells, a point source at `(2, 64)`, and a
right-edge connection target. Each aperture contributes a scalar cylindrical
wavelet with amplitude proportional to `1/sqrt(r)` and phase `kr`. The coherent
field squares the summed complex amplitudes; the path-tagged field sums the two
aperture intensities and removes their cross term.

## Two-scale Earth implementation

### Native optical reference

Use a narrowband `450 nm` common-source laser and set one Rust optical cell to
`450 nm / 8 = 56.25 nm`.

| Quantity | Native optical value |
|---|---:|
| Grid | `10.800 × 7.200 µm` |
| Barrier coordinate | `x = 2.025 µm` |
| Source-to-barrier distance | `1.9125 µm` |
| Clear width of each slit | `506.25 nm` |
| Slit center separation | `1.800 µm` |
| Barrier-to-final-plane distance | `8.71875 µm` |
| Expected far-plane fringe spacing, `λz/d` | `2.1797 µm` |

With slit half-width `a = 253.125 nm`, the final-plane Fresnel number is

```text
F = a² / (λz) = 0.01633.
```

At the first cell beyond the barrier, `F = 2.531`; the simulated longitudinal
map therefore spans the near-field/Fresnel region into a low-Fresnel-number
output plane.

Fabricate the optical reference as two `506 ± 20 nm` clear apertures in a
`100 nm` chromium mask on fused silica, centered `1.800 ± 0.025 µm` apart.
Measure the longitudinal field at selected planes from `z = 0.5` to `8.72 µm`
with calibrated high-NA microscopy or near-field mapping. This coupon supplies
the measured coherent and tagged intensity maps and the Maxwell-validation
geometry.

### Magnified conductive-growth plane

Hwang et al. demonstrated DMD-addressed photoelectrochemical PEDOT patterning
at `1.5 ± 0.2 µm` resolution. Use `1.5 µm` as the real growth-cell pitch and a
`26.6667×` calibrated relay from the native optical field.

| Quantity | PEDOT growth-plane value |
|---|---:|
| Grid | `288 × 192 µm` |
| Barrier coordinate | `x = 54 µm` |
| Source coordinate | `(3 µm, 96 µm)` |
| Source-to-barrier distance | `51 µm` |
| Clear width of each slit | `13.5 µm` |
| Slit center separation | `48 µm` |
| Barrier-to-right-edge distance | `232.5 µm` |
| Magnified fringe spacing | `58.125 µm` |

Pattern a `1.5 µm`-wide Parylene-C/SU-8 insulating barrier across a
Parylene-coated glass floor with the two clear `13.5 µm` apertures. Use a
lithographic Au source pad at the left-center seed and an Au collection rail at
the right edge. The resulting `288 µm` working length fits the established
wet-cell scale while retaining every Rust geometry ratio.

The chemistry is the existing Earth candidate: fresh aqueous `10 mol m⁻³`
EDOT + `10 mol m⁻³` 1,4-benzoquinone + `1 mol m⁻³` NaPSS, with PEDOT:PSS as the
developing conductor. The optical relay projects the measured coherent or
path-tagged dose map onto this growth plane; the physical barrier simultaneously
constrains lateral surface recruitment to its two apertures.

## Coherence and path tagging

- **Coherent condition:** illuminate both apertures from one spatially filtered
  laser with matched parallel polarization, path mismatch `≤100 µm`, and
  measured coherence length `≥10 cm`. Lock relative phase at the field map used
  for projection.
- **Path-tagged condition:** place orthogonal polarization markers on the two
  apertures, following the demonstrated double-slit path-marking method. Record
  both polarization channels and sum their intensities before projection.
- **Polarization-control condition:** scramble one arm's relative phase over
  `0–2π` faster than the material integration time while preserving the same
  per-aperture envelope. Agreement between orthogonal tagging and phase
  scrambling identifies cross-term removal independently of PEDOT polarization
  sensitivity.
- Match incident and projected total optical energy between conditions within
  `2%`; also retain the Rust-style peak-normalized maps for direct morphology
  comparison.

## Exposure, switch, and observation

Use `450 ± 5 nm` projection at `10 W m⁻²` for a primary `300 s` growth window,
giving `3.0 kJ m⁻²` (`0.30 J cm⁻²`) incident fluence. A matched `100 W m⁻²`
cohort supplies the predeclared high-dose bracket already present in the Earth
manifest. Maintain the cell at `295 ± 2 K`, measure irradiance at the specimen,
and record temperature beside the sealed droplet.

Drive the PEDOT cell with the calibrated bipolar growth waveform under the
existing independent current compliance. For history-switch conditions, switch
the optical map at `150 s` and also report the switch at `50%` of integrated
growth charge. The time switch matches the model's halfway step; the charge
coordinate matches its halfway material budget.

Record synchronized inverted bright-field/fluorescence images at `≥10 frame/s`,
the projected map, photodiode trace, waveform, current, conductance, temperature,
and cumulative charge. Score route completion at the right collection rail,
centroid and branch alignment with each optical map, aperture occupancy, bridge
time, resistance, and deposited area. Use post-run SEM or AFM for submicron
branch and barrier geometry.

## What the scalar model preserves

The Rust field preserves:

- aperture width, separation, wavelength, and observation distance as exact
  dimensionless ratios;
- phase accumulation with geometric path length;
- coherent complex-amplitude addition and the path-tagged removal of the cross
  term;
- two-dimensional cylindrical spreading through the `1/sqrt(r)` envelope;
- normalized spatial preference supplied to growth;
- equal step/material budgets, stochastic local recruitment, and the direction
  of the halfway history switch.

Its result is therefore an exact test of **field-map × accumulated-material
history** within the reduced law.

## Maxwell/FDTD admission check

Run a three-dimensional dispersive FDTD model of the native fused-silica/
chromium aperture coupon using measured mask thickness, complex refractive
indices, finite beam waist, and the same parallel/orthogonal polarization
conditions. Use `≤10 nm` cells at aperture edges, a converged coarser mesh away
from metal, and PML boundaries. A band-limited angular-spectrum calculation
provides an independent scalar propagation check before FDTD.

Measure and compare:

1. complex `E` and `H`, time-averaged Poynting flux, and `|E|²` in the growth
   slice;
2. slit transmission balance, phase difference, fringe period, peak locations,
   and visibility `V = (Imax-Imin)/(Imax+Imin)`;
3. residual tagged visibility and coherent cross-term energy;
4. reflection, standing-wave structure, evanescent edge fields, and absorbed
   power in chromium, substrate, electrolyte, and deposited PEDOT;
5. correlation of scalar and FDTD intensity after convolution with the measured
   relay/DMD point-spread function; and
6. field redistribution after inserting segmented PEDOT geometries from early,
   middle, and bridged growth states.

Predeclare admission as: per-aperture transmitted powers matched within `2%`,
far-plane fringe-period error `≤5%`, tagged residual visibility `≤0.05`, and
scalar/FDTD intensity correlation `≥0.90` after measured optical convolution.
The FDTD absorbed-power and vector-field maps then become the optical dose used
by the next material-growth model.

## Primary sources

- Janzakova et al. (2021), [analog programming of conducting-polymer dendritic
  interconnections](https://doi.org/10.1038/s41467-021-27274-9).
- Hwang et al. (2025), [light-guided patterning of electroactive PEDOT on
  hematite](https://doi.org/10.1016/j.cej.2025.168284).
- Walborn et al. (2002), [double-slit polarization path marking and quantum
  erasure](https://doi.org/10.1103/PhysRevA.65.033818).
- Matsushima and Shimobaba (2009), [band-limited angular-spectrum propagation](https://doi.org/10.1364/OE.17.019662).
- Oskooi et al. (2010), [Meep FDTD electromagnetic simulation](https://doi.org/10.1016/j.cpc.2009.11.008).
