# Voltage-routing benchmark

## Question

Can a field-grown conductor deliver voltage with less material than a redundant
parallel grid while retaining more alternate structure than a single prescribed
wire?

The first benchmark evaluates three topologies under identical one-volt
boundaries:

1. a three-pixel straight wire;
2. a five-rail parallel grid with terminal bus bars;
3. the seed-319 conductor developed under the Cherenkov-cone field.

MOOSE solves the steady conduction equation
`div(sigma(x, y) * grad(V)) = 0` on each image-derived topology. Metal pixels
have normalized conductivity `1`; the surrounding medium has conductivity
`1e-6`. The primary outputs are terminal flux, occupied material fraction, and
flux per occupied fraction.

The straight wire supplies the material-minimum reference. The grid supplies
the redundant fixed-interconnect reference. The developed conductor is tested
between them. A second stage cuts one equal-width segment in each topology and
repeats the solve; a third stage introduces obstacles and moving terminals.

The first solve and cut result are reported in [`RESULTS.md`](RESULTS.md).

## Unanswered construction questions

- Can local field-guided growth approach Steiner-like multi-terminal routing
  without an externally calculated graph?
- Does developed redundancy preserve conductance after a cut more efficiently
  than regular parallel rails?
- Can growth and pruning track moving loads while fixed interconnects require a
  new routing solution?
- Does the substrate's physical relaxation solve useful inverse-field problems
  before their state is translated into a digital adjacency matrix?
- Which morphology maximizes delivered conductance per unit material while
  bounding heat, noise, and destructive shorts?

These questions compare physical development with prescribed interconnects.
Voltage transport, perturbation recovery, and material efficiency establish
the computational function of each topology.
