# Native MOOSE voltage-coupled growth

This is the smallest developing-conductor candidate in which morphology and
voltage evolve inside one MOOSE solve. No Rust topology is imported.

## Coupling

The conductive order parameter `eta` follows anisotropic Allen–Cahn dynamics.
MOOSE simultaneously solves

```text
div(conductivity(eta) * grad(voltage)) = 0
```

with normalized source and sink potentials of `1` and `0`. Conductivity rises
smoothly from `0.01` in the medium to `1` in the conductive phase. The live
voltage field changes phase mobility:

```text
mobility(voltage) = 80 * (1 + 3 * voltage^2)
```

The resulting loop is:

```text
eta -> conductivity -> voltage -> mobility -> eta
```

A diffusing thermal field receives latent heat from phase change. The run is
dimensionless and establishes native coupling, not a calibrated metal system.
Ion conservation, Nernst–Planck electromigration, Joule heat, mechanics,
optical absorption, and a finite material reservoir remain explicit next
physics additions.

## Run

```sh
MOOSE_BIN=/path/to/moose-opt
"$MOOSE_BIN" --check-input -i native_voltage_growth.i
"$MOOSE_BIN" -i native_voltage_growth.i
```

The CSV records phase amount and both terminal fluxes at each timestep; Exodus
stores `eta`, `temperature`, `voltage`, and `conductivity` for volumetric
inspection.

## First run

The committed candidate passed `--check-input` and converged through all 20
timesteps with MOOSE snapshot commit `08315af82e`.

| Quantity | First solved step | Final step (`t = 0.02`) |
|---|---:|---:|
| Conductive phase integral | `0.006819` | `0.015792` |
| Sink flux | `0.006869` | `0.007054` |

The phase amount increased 2.32-fold while voltage and conductivity were solved
inside the same nonlinear system. [`native_voltage_growth.png`](native_voltage_growth.png)
shows the final phase and potential fields.
