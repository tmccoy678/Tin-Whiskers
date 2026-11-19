# Simulation route

The simulation asks whether field-guided material growth can become a
history-bearing topology before any physical substrate is purchased.

## Five stages

1. **High-fidelity physics** — use validated phase-field and level-set models
   for electricity, ion transport, diffusion, heat, flow, and moving material
   boundaries.
2. **Small physical calibration** — use one transparent dish to measure the
   material parameters that must be determined experimentally.
3. **Model reconciliation** — require simulated and observed morphology,
   conductance, and time scales to agree within stated tolerances.
4. **Reduced Rust model** — preserve the calibrated relationships in a fast,
   inspectable simulator suitable for large parameter sweeps.
5. **Photon-choice comparison** — compare closed-loop AI/SI photon choices
   with an identical yoked replay before interpreting growth as interest,
   learning, repair, or autopoiesis.

## Installed local engine

The private Studio workspace uses the official prebuilt Apple Silicon MOOSE
binary. Third-party examples and generated simulation outputs remain under the
ignored `simulation/work/` and `simulation/output/` directories.

COMSOL's diffusion-controlled electrodeposition example is the preferred
high-fidelity reference model. Running it for this project requires a lawful
research or evaluation license; the UW teaching license excludes research use.

