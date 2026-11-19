# Materials calibration: Earth proof and vacuum/space path

## Decision

Use two deliberately separate material systems.

1. **Earth proof of principle:** aqueous PEDOT:PSS dendrites between gold
   electrodes. This is the fastest route to a visible, conductive, field-grown
   bridge with a finite reservoir and published geometry.
2. **Vacuum/space reliability:** a hermetically capped Ag/Ag-doped
   Ge\(_{30}\)Se\(_{70}\)/Ni conductive-bridge cell array. This replaces the
   volatile liquid with a solid ion conductor and permits reversible filament
   growth from a bounded Ag reservoir.

Tin whiskers remain a later failure comparator, not the first growth medium.
Their stress-driven nucleation is poorly addressable and their normal
engineering significance is unintended shorting, whereas both selected systems
offer an explicit reservoir and an electrical stop condition.

Values below are either **established** for a cited experiment or **proposed**
as the first calibration setting. Values from a related stack are not treated
as properties of the proposed device.

## 1. Safe Earth-lab proof of principle

### Established anchor

Janzakova et al. grew PEDOT dendrites in a `20 µL` aqueous drop containing
`10 mol m^-3` EDOT, `10 mol m^-3` 1,4-benzoquinone (BQ), and `1 mol m^-3`
NaPSS. The electrodes were `25 µm` Au wires separated by `240 µm` over
Parylene-C-coated glass. Cyclic voltammetry found an electropolymerization
threshold near `0.9 V`; at `80 Hz`, `50%` duty, and zero offset, published
bridges formed in about `423 s` at a `3.5 V` peak and `178 s` at `5 V`.
Frequencies below `10 Hz` produced bubbling in that setup. These are exact-stack
anchors from the [primary growth study](https://doi.org/10.1038/s41467-021-27274-9).

The companion electrical study used `10 V` peak-to-peak bipolar growth and
reported bridge conductance of order `0.1-0.3 mS`; its image-reconstructed
resistivity plot spans approximately `0.007-0.045 Ω m`, or roughly
`20-140 S m^-1`, as frequency rises from `40` to `320 Hz`. Those are graphical,
model-dependent readings, not a universal PEDOT constant. Low-voltage readout
at `0.1 V` and ionic gating at `±0.4 V` were demonstrated without continuing
EDOT oxidation. See [Janzakova et al., *Advanced Science*
(2021)](https://doi.org/10.1002/advs.202102973).

A separate system has used DMD-addressed visible photoelectrochemistry on a
hematite photoanode to pattern PEDOT with `1.5 ± 0.2 µm` resolution. It
establishes an optical-interface route, but not optical steering of the Au-wire
dendrites above; combining the two is therefore a test, not an established
fact. See [Hwang et al., *Chemical Engineering Journal*
(2025)](https://doi.org/10.1016/j.cej.2025.168284).

### Proposed first cell

| Element | Proposed starting specification |
|---|---|
| Conductor / medium | PEDOT:PSS grown in fresh aqueous `10 mol m^-3` EDOT + `10 mol m^-3` BQ + `1 mol m^-3` NaPSS |
| Electrodes / geometry | Two `25 µm` Au wires, `240 ± 10 µm` tip gap, active length `0.5 mm`; Parylene-C glass floor and sealed coverslip |
| Reservoir | `20.0 ± 0.5 µL`; this contains `2.0e-7 mol` EDOT, at most about `28.4 µg` monomer before yield and counter-reaction losses |
| Growth drive | Bipolar square wave, `10 Vpp` (`±5 V`), `80 Hz`, `50%` duty, zero DC offset; hard current compliance `2 mA`; stop on first electrical bridge or `300 s` |
| Read drive | `0.10 V` for `100 ms`, compliance `200 µA`; report conductance in siemens and infer conductivity only from the imaged 3-D estimate |
| Conductivity gate | Proposed admission: bridge conductance `>=50 µS` and model-derived effective conductivity `>=10 S m^-1`; record the full value rather than substituting bulk PEDOT data |
| Temperature / pressure | `295 ± 2 K`, `101 ± 5 kPa`; no vacuum claim |
| Optical interface | Inverted bright-field microscope plus DMD-projected `450 nm` LED corridor, `50 µm` wide; irradiance sweep `0, 10, 100 W m^-2`, measured at the cell with a calibrated photodiode |

**Oxidation and passivation.** EDOT oxidation is the intended growth reaction;
BQ reduction is the paired counter-reaction and PSS is the dopant. Gold is the
exposed electrode. Parylene-C covers the glass and non-active lead length, but
must not cover the final `0.5 mm` growth zone. Seal the drop to make evaporation
and oxygen exposure common across illuminated and dark lanes. A post-growth
Parylene overcoat is allowed only for a separate dry-retention specimen because
it freezes access to the live reservoir.

**Safety boundary.** “Safe Earth-lab” means microlitre scale in a ventilated
chemical enclosure with splash goggles, compatible gloves, secondary
containment, and collected hazardous waste—not an open household bench. The
current Sigma-Aldrich BQ SDS classifies the supplied solid for acute toxicity
and skin corrosion; follow the lot-specific SDS before work
([manufacturer SDS](https://www.sigmaaldrich.com/US/en/sds/sial/phr1028)).

### Instrumentation and measurements

- waveform generator plus source-measure unit with independent current trip;
- synchronized microscope video, DMD pattern log, calibrated photodiode, and a
  temperature probe beside the drop;
- pre/post impedance from `10 Hz` to `100 kHz` at `10 mVrms`, plus `0.1 V`
  conductance reads;
- from every frame: tip position, projected area, branch count, bridge time,
  local optical dose, charge, electrical energy, and reservoir mass budget.

### Smallest falsifying Earth experiment

Use six fresh dual-gap chips. On each chip, drive two nominally identical gaps
with the same synchronized waveform; project the `450 nm`, `100 W m^-2`
corridor toward one gap and deliver a spatially uniform, equal-energy exposure
to the paired control. Swap left/right assignment between chips. The optical
steering claim fails at this stage if fewer than five of six illuminated lanes
move their tip centroid toward the corridor **or** if the paired median change
is smaller than `25 µm` and `20%` in bridge time. An electrical bridge without
that paired displacement proves electropolymerization, not photon-directed
growth.

## 2. Vacuum/space-reliability regime

### Established anchor

Programmable metallization cells use Ag oxidation, Ag-ion motion through a
solid chalcogenide, and reduction at an inert electrode to form and dissolve a
conductive bridge. Ag-Ge-Se devices have demonstrated incremental resistance
states ([Mahalanabis et al., 2014](https://doi.org/10.1016/j.sse.2014.07.002)).
A closely related Ag/Ag-Ge-S/W stack cycled below `0.6 V` at programmed currents
of `0.27, 1.6, 55, and 220 µA`, retained an OFF/ON ratio above 10, and showed no
substantial speed change through `1.5e6` program/erase operations
([Kamalanathan et al., 2011](https://doi.org/10.1088/0957-4484/22/25/254017)).
Those values bound the first electrical sweep; they are not assumed endurance
for the selected Ge-Se stack.

Bulk Ag conductivity is approximately `6.1e7 S m^-1` near room temperature
([IAEA conductor table](https://www-pub.iaea.org/MTCD/Publications/PDF/TCS-48_web.pdf)).
A nanoscale, discontinuous filament may be orders of magnitude lower, so the
device observable is conductance; conductivity is reported only after filament
cross-section is measured by post-test TEM.

During in-situ cobalt-60 exposure, Cu-SiO2 and Ag-Ge30Se70 CBRAM showed no TID
effect in DC I-V sweeps beyond `1 Mrad`, but pulse-programmed conductance change
decreased with accumulated dose. Dynamic programming is therefore the
radiation-sensitive test, not merely an unbiased retention read
([Taggart et al., 2018](https://doi.org/10.1109/TNS.2017.2779860)). A NASA
single-event study likewise found a commercial stand-alone CBRAM immune to
standby bit upsets while identifying active peripheral circuitry as a separate
risk; that product result does not qualify this material stack
([NASA NEPP report](https://nepp.nasa.gov/files/27878/NEPP-CP-2015-Chen-Poster-NSREC-TN24782.pdf)).

### Proposed solid-state coupon

| Element | Proposed starting specification |
|---|---|
| Conductor / growth medium | Ag filament in Ag-photodoped amorphous Ge30Se70 |
| Electrodes / geometry | `100 µm × 100 µm` vertical cell; `30 nm` Ag active electrode / `80 nm` Ge30Se70 / `100 nm` Ni or Pt inert electrode; 8 × 8 array on fused silica |
| Reservoir | The `30 nm` Ag layer over one cell is about `3.15 ng` at `10,492 kg m^-3`; count the full film and any photodoped Ag against the mass budget |
| Set/reset/read | Begin at `0.05 V` read; sweep `0 -> +0.6 -> 0 -> -0.6 -> 0 V`; compliance ladder `1, 10, 100 µA`; never exceed `0.8 V` until the exact stack's breakdown distribution is measured |
| Electrical admission | Stable, reversible conductance states spanning at least 10:1; proposed useful ON range `10 µS-1 mS`; no spontaneous SET during a `24 h` unbiased hold |
| Conductivity report | Quote `G` directly. Calculate `σeff = GL/A` only for cells whose filament `A` is measured; compare with bulk Ag, never assign bulk Ag conductivity to the filament |
| Pressure / temperature | Vacuum screen `<=1.3e-3 Pa`; eight cycles from `233` to `358 K` (`-40` to `+85 °C`), ramp `<=2 K min^-1`, `60 min` stabilized dwell at each extreme |
| Optical interface | `405 nm` exposure through fused silica for calibrated Ag photodoping during fabrication; for operation, a `450 nm` photodiode/micro-LED address converts local photon dose into the bounded set pulse. Direct light steering of the buried Ag filament is unproven and is not claimed. |

**Oxidation and passivation.** Ag -> Ag+ at the active electrode and Ag+ -> Ag
at the inert electrode are intended; reverse bias dissolves the bridge. Cap the
finished stack with `20-50 nm` ALD Al2O3 or SiNx and hermetically seal the
coupon. Use Au over the external Ag contact pad to limit tarnish while leaving
the internal Ag/electrolyte interface unblocked. The solid Ag film is the only
growth reservoir; any state change after its measured inventory is exhausted
is failure, not self-supply.

### Reliability sequence and instruments

1. **Vacuum first:** compare 12 cells at `293 K` in air with 12 under
   `<=1.3e-3 Pa`, 100 set/reset cycles per cell. Record `Vset`, `Vreset`, pulse
   energy, ON/OFF conductance, retention, and spontaneous transitions.
2. **Thermal-vacuum:** run the eight proposed cycles while reading at both
   plateaus and programming once per plateau. NASA guidance calls for vacuum
   thermal cycling with temperature limits derived from the mission and at
   least `10 K` beyond expected flight extrema; the `233-358 K` screen must be
   replaced by mission-specific limits before qualification
   ([NASA-STD-7002B](https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7002B-w-Change-1.pdf),
   [GSFC GEVS](https://standards.nasa.gov/node/791)).
3. **Radiation after environmental survival:** expose separate active-program
   and unbiased-retention groups to `0.1, 1, 3, and 10 kGy(Si)` cobalt-60 TID
   (`10, 100, 300, 1000 krad(Si)`). At each step repeat the same pulse train.
   Heavy-ion SEE and displacement-damage levels remain mission-specific; do not
   invent them before orbit, shielding, and lifetime are named.

Use a vacuum probe station with temperature chuck, guarded SMU and pulse
measurement unit, thermocouples on the coupon, chamber pressure gauge, residual
gas analyzer, calibrated radiation dosimetry, and synchronized optical power
monitor. Reserve SEM/TEM, XPS, and Raman for failed and endpoint coupons; they
determine filament geometry, Ag oxidation state, cap integrity, and
chalcogenide change rather than serving as routine cycle instrumentation.

Proposed rejection thresholds are: any hard short; any cap delamination or
measurable reservoir loss; more than `20%` drift in median `Vset`, ON
conductance, or pulse-programming efficacy at the chosen mission dose; ON/OFF
ratio below 10; or spontaneous switching above `1e-6` per cell-hour.

### Smallest falsifying vacuum experiment

Before thermal cycling or irradiation, run the 12-air/12-vacuum comparison at
`293 K`. The candidate fails the vacuum gate if more than one of 12 vacuum cells
cannot complete 100 reversible cycles, if any hard short occurs, or if the
vacuum group's median `Vset` or ON conductance differs from the air group by
more than `20%`. This one test can reject the stack before expensive radiation
work while preserving the exact failure signatures needed to choose a better
cap, electrolyte, or reservoir.

## Admission order

Admit the Earth cell only after electrical reproduction and the paired optical
test pass. Admit the solid-state stack only after vacuum, thermal-vacuum, then
active-program radiation gates pass in that order. Neither regime by itself
establishes adaptive intelligence, autopoiesis, or space qualification; it
calibrates the material response that a later fixed or adaptive controller must
earn against matched energy, mass, and damage budgets.
