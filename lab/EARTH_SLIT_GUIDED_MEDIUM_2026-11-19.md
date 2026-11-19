# Earth slit-guided growth medium

Status: buildable first-cell specification for translating the Rust
slit-guided topology result into an Earth-lab experiment.

## Selection

Use **photoelectrochemically grown PEDOT on nanorod hematite/FTO glass**.
Hwang, Bang, and Kim demonstrated spatially addressed PEDOT growth on
photoactive hematite from millimeter scale down to `1.5 ± 0.2 µm` resolution
([primary study](https://doi.org/10.1016/j.cej.2025.168284)). The hematite turns
the incident light field into local holes that oxidize EDOT; the deposited
PEDOT persists as an electroactive conductive pattern. This mechanism gives the
Rust slit a direct physical meaning: illuminated aperture geometry controls
where conducting matter forms.

The PEDOT–hematite cell is the strongest first medium because it combines:

- demonstrated visible-light spatial control;
- a transparent, imageable aqueous interface;
- low-voltage electrochemistry;
- a countable finite monomer reservoir;
- micron-scale pattern resolution;
- conductance readout during and after development; and
- a two-channel optical actuator that maps cleanly to the adaptive controller.

## First-cell specification

| Element | Starting specification |
|---|---|
| Conductor | Electroactive PEDOT deposited by local photoelectrochemical oxidation of EDOT |
| Photoactive host | `671 ± 20 nm` nanorod hematite film on `1.0 mm` FTO-coated borosilicate glass, following the demonstrated platform |
| Growth medium | `10 µL` covered aqueous drop: `8 mM` EDOT, `0.20 M` LiClO₄, `2 mM` SDS; prepare in glass, mix for one hour, use fresh at `295 ± 2 K`. The composition is anchored by published aqueous PEDOT electropolymerization ([primary electrolyte study](https://doi.org/10.1007/s10008-020-04809-6)) |
| Finite reservoir | `80 nmol` EDOT in the `10 µL` drop, equal to an `11.4 µg` monomer upper bound before polymerization yield and counter-ion mass |
| Sense electrodes | Two lithographic Ti/Au pads terminating in `25 µm` tips, `240 ± 10 µm` apart on the hematite/FTO surface; FTO/hematite remains the photoanode and the Au tips provide a separate low-bias source-to-sink conductance measurement |
| Reference / counter | Ag/AgCl reference and Pt-wire counter electrode in a covered three-electrode microcell |
| Optical source | Stabilized `450 nm` LED coupled through a 1×2 splitter into two `200 µm`-core, NA `0.22` silica fibres; independent shutters or current drivers provide the upper/lower controller actions |
| Apertures | Each fibre images through a chrome-on-glass `50 µm × 300 µm` slit via a `10×` objective. Two parallel corridors span the Au-pad gap with `100 µm` centre separation. The source plane stays fixed for the whole run |
| Optical dose | Calibrated irradiance ladder `10, 30, 100 W m⁻²`; first paired test at `100 W m⁻²`. A `50 × 300 µm` corridor receives `1.5 µW`, or `0.45 mJ` over the `300 s` maximum growth interval |
| Growth potential | Measure each chip's illuminated EDOT-oxidation onset by a short linear sweep, then hold at `E_onset + 0.10 V`, capped at `+0.84 V vs Ag/AgCl`; current compliance `100 µA`; growth window `300 s` |
| Bridge read | Pause growth every `5 s`; apply `50 mV` pad-to-pad for `100 ms` with `10 µA` compliance. Stop on `G ≥ 10 µS`, current trip, visible gas, `2 K` temperature rise, or the time limit |

The `0.84 V vs Ag/AgCl` cap follows aqueous PEDOT work that selected this
potential to support polymerization while preserving polymer quality. The
earlier Au-wire dendrite system supplies the `240 µm` bridge scale and confirms
that aqueous PEDOT can form visible conductive bridges in a finite drop
([Janzakova et al.](https://doi.org/10.1038/s41467-021-27274-9)).

## Fabrication and measurement route

1. Grow the nanorod hematite layer hydrothermally on FTO glass and verify film
   continuity and thickness by profilometry plus one sacrificial SEM section.
2. Pattern the paired Ti/Au sense pads, passivate the leads, and leave the
   `240 µm` growth window open over hematite.
3. Assemble the covered `10 µL` three-electrode microcell in secondary
   containment. Record the dark and illuminated onset curves before the growth
   trial.
4. Image both calibrated slits on the empty cell, freeze their coordinates, and
   record power at the sample plane with a calibrated photodiode.
5. Alternate the controller's upper/lower equal-energy light actions while the
   potentiostat holds the bounded photoelectropolymerization potential.
6. Synchronize microscope frames, selected slit, optical dose, current, charge,
   temperature, and pad-to-pad conductance.
7. Quantify PEDOT-mask overlap, centreline displacement, branch/tip count,
   deposited charge, bridge time, final conductance, and charge per connected
   micrometre. Preserve the chip for Raman confirmation and endpoint
   profilometry.

The fibres and fixed apertures provide a sparse optical body: two stable light
channels, two material consequences, and one transparent developing field.
Equal-energy shutter commands give the controller bounded fingers while the
hematite and electrolyte determine the detailed anatomy.

## Smallest safety-bounded falsifier

Use **six chips**, each carrying two geometrically matched pad gaps. Randomize
upper/lower placement and analyst labels.

- **Slit-guided lane:** the `50 µm` corridor connects the source and sink tips.
- **Yoked lane:** receives the same `450 nm` energy and timing through a slit
  shifted `100 µm` away from the source–sink centreline.
- Both lanes share electrolyte batch, temperature, potential, current
  compliance, exposure time, and total charge ceiling.

The optical mechanism advances when at least five of six chips show both:

1. greater PEDOT overlap with the illuminated source–sink corridor than with
   the shifted yoke; and
2. either a paired centroid displacement of at least `25 µm` toward the active
   slit or at least `20%` improvement in charge-to-bridge.

The result becomes especially informative when bridge conductance, charge,
mask overlap, and endpoint Raman signal agree. Each favorable component earns a
focused follow-up: wavelength sweep, slit-width sweep, action timing, or
closed-loop reversal.

## Safety and stop architecture

Run inside a ventilated chemical enclosure with the `450 nm` beam fully
enclosed, interlocked source power, splash goggles, compatible gloves,
secondary containment, and collected perchlorate/EDOT waste. The potentiostat
enforces the `0.84 V`, `100 µA`, and `300 s` ceilings independently of control
software. Visible gas, temperature rise, compliance, bridge detection, or
liquid leakage opens the electrical and optical relays and preserves the last
synchronized frame.

This first experiment asks one exact question: **does a sparse visible-light
slit causally guide persistent conductive PEDOT growth across a measured gap?**
Its answer supplies the physical calibration for the Rust photon-gain term and
the next adaptive/yoked experiment.
