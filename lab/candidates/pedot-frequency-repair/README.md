# PEDOT frequency-informed cut and repair

Status: completed literature-informed screening experiment.

## Question

How does the same current-driven conductive body repair the same literal cut
across the measured PEDOT transition from broad dendritic growth toward
oriented cable-like growth as waveform frequency rises?

## Translation and controls

Janzakova et al. measured PEDOT dendrites grown with square-wave drive from
`10–950 Hz`. Projected area varied approximately with waveform period, while
increasing frequency shifted morphology from diffuse dendrites toward oriented
linear cables. The candidate translates those two observed relationships into
the established `192 × 128` current-driven remodeling instrument:

- growth probability receives the normalized period factor `80 Hz / f`;
- a log-frequency coordinate blends four-neighbor diffuse recruitment toward
  horizontally oriented recruitment;
- voltage, `50%` duty, initial cut, conductivity solve, optical probes, seed,
  epoch count, and source/sink geometry remain fixed.

This translation is a screening law. Its purpose is to test the consequence of
the published frequency ordering inside the repair mechanism; physical PEDOT
calibration remains the next bench measurement.

Primary source: Janzakova, K., Kumar, A., Ghazal, M., et al. (2021).
[Analog programing of conducting-polymer dendritic interconnections and control
of their morphology](https://doi.org/10.1038/s41467-021-27274-9). *Nature
Communications, 12*, 6898.

## Results

| Frequency | First connection | Final flux ratio | Material ratio | Lower peak current per delivered current |
|---:|---:|---:|---:|---:|
| `10 Hz` | epoch **5** | **46.660×** | 3.561× | **93.849%** |
| `80 Hz` | epoch **18** | **7.842×** | 1.405× | **72.116%** |
| `320 Hz` | developing through epoch 36 | **2.388×** | 1.117× | **22.487%** |
| `950 Hz` | developing through epoch 36 | **1.305×** | 1.049× | **12.317%** |

Across the matched 36-epoch horizon, the literature-informed transition
produced a 35.74-fold span in final terminal flux. The 10 Hz body recruited the
largest material volume and restored connectivity first; 80 Hz restored a
finer connected route; 320 and 950 Hz preserved increasingly narrow developing
routes. These positive phenotypes define the next ensemble and physical-cell
tests.

## Visual evidence

The two-chapter movie shows two full-width anatomies at once:

1. `10 Hz` beside `80 Hz`, with holds at first reconnection epochs 5 and 18;
2. `320 Hz` beside `950 Hz`, showing the developing oriented routes.

Every white pixel is one literal occupied cell and every displayed movie state
comes from one MOOSE-evaluated remodeling epoch.

[Open the 192 × 128 cut/repair movie](../../../figures/pedot-frequency-cut-repair-10-80-320-950Hz.mp4)

## Reproduction

`run.py` uses the established MOOSE voltage/conduction model and accepts:

```sh
PEDOT_FREQUENCY_HZ=80 \
REMODEL_EPOCHS=36 \
REMODEL_SOURCE=simulation/voltage-routing/topologies/grown-transect-60-cut.png \
REMODEL_NAME=pedot_frequency_repair_80Hz \
python run.py
```

The scientific Python environment used for the admitted run contains NumPy,
Pillow, and PyVista; MOOSE performs the normalized field solve. The proposed
Rust-first successor will own the frequency field, growth, audit, and VTK/image
output in one compiled instrument, with MOOSE retained as the independent
field verifier.

## Integrity

| Artifact | SHA-256 |
|---|---|
| `10Hz-metrics.tsv` | `5c0a3ea389a711407b23fd0fcddc8794f770bfd4dc5cc5543139fb2eaec54535` |
| `80Hz-metrics.tsv` | `36b512d8f3fd7451ab0fcae053ad8a8f7651690b2983697c6cac6050b78a6bcc` |
| `320Hz-metrics.tsv` | `eb1caa1e737005c9d5680edb5535d506b8e0ef1fd9514860ee6a3490fe1ec330` |
| `950Hz-metrics.tsv` | `8dcec2b70b4db22c6a525008d5997a3d82eb4ee041ac277e11e2633e15aad5f8` |
| H.264 movie | `5112e36e62e61700d950c1f05648f003674f98b793918af2d7f9b77ca45fbf72` |
