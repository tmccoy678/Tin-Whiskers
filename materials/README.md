# Material program

## Current selection

**Silver is the first photonic-growth candidate. Copper is the first scalable
conductive-growth candidate.** Aluminum, tin, and nickel contribute distinct
traits that should be tested separately before any mixed substrate is built.

The selection follows demonstrated coupling mechanisms:

| Material | Established trait | Experimental role |
|---|---|---|
| Silver | Plasmon excitation can control anisotropic particle growth, including fusion and light-selected final size. Electrodeposition can also produce hierarchical nanodendrites with optically active hotspots. | First test of a conductor whose growing geometry both responds to light and changes later optical response. |
| Copper | Laser irradiation can localize electrodeposition and increase cathodic current density; copper also supplies high electrical conductivity at ordinary material cost. | First scalable test of photon-conditioned conductive path growth. |
| Aluminum | Nanostructures support ultraviolet-to-visible plasmonic behavior across a broad spectral range. | Optical boundary and field-concentration layer. |
| Tin | Spontaneous whisker growth reflects compressive stress state; engineered tin@carbon whiskers show broad electromagnetic-wave absorption. | Later test of stress-responsive growth and radio-frequency interaction. |
| Nickel | Pure-metal phase-field models reproduce dendritic solidification with coupled phase and thermal fields. | High-temperature morphology benchmark and validation case. |

Silver currently offers the shortest path from photon allocation to persistent,
readable morphology. Copper offers the shortest path from the reduced model to
a low-cost electrodeposition experiment. Their first experiments remain
separate so that optical response, deposition kinetics, oxidation, and galvanic
effects can be attributed to one material system at a time.

## Computational sequence

1. Map the reduced model's photon gain across the range where topology changes
   while the electric drive and pseudorandom seed remain fixed.
2. Apply a Cherenkov-cone photon field with
   `cos(theta) = 1 / (beta * n)` and record how branch occupancy changes along
   and outside the cone.
3. Calibrate a silver-inspired regime from measured light-controlled growth
   rates and a copper-inspired regime from measured laser-induced current and
   deposition rates.
4. Reconcile both regimes against a phase-field or level-set model before
   assigning physical dimensions to the reduced simulator.
5. Compare closed-loop photon allocation with its exact yoked replay in each
   calibrated material regime.

The reduced simulator presently carries dimensionless parameters. Material
names enter its results after a published or measured quantity defines the
mapping.

The full element, substrate, frequency, and planetary condition framework is
defined in [`SEARCH_SPACE.md`](SEARCH_SPACE.md). Planetary morphologies and
surviving natural structures are routed through
[`PLANETARY_PRIORS.md`](PLANETARY_PRIORS.md).

## Primary sources

- Jin, R., Cao, Y. C., Hao, E., et al. (2003). [Controlling anisotropic
  nanoparticle growth through plasmon
  excitation](https://doi.org/10.1038/nature02020). *Nature, 425*, 487–490.
- Luna-Cervantes, M., Santos-Santiago, E. O., Jiménez-Girón, D., et al.
  (2026). [Electrolyte- and hydrodynamics-controlled potentiostatic growth of
  Ag nanodendrites on metallic Ti for SERS
  detection](https://doi.org/10.1021/acsomega.6c01538). *ACS Omega, 11*,
  32691–32712.
- Wei, H., Ren, W., Xu, J., et al. (2025). [Femtosecond laser-induced
  localized electrodeposition of two dimensional metal
  patterns](https://doi.org/10.1016/j.optlastec.2025.112854). *Optics & Laser
  Technology, 187*, 112854.
- Gérard, D., & Gray, S. K. (2015). [Aluminium
  plasmonics](https://doi.org/10.1088/0022-3727/48/18/184001). *Journal of
  Physics D: Applied Physics, 48*, 184001.
- NASA Goddard Space Flight Center. [Basic information regarding tin
  whiskers](https://nepp.nasa.gov/whisker/background/).
- Hu, F., Ding, P., Wu, F., et al. (2024). [Novel cable-like tin@carbon
  whiskers derived from the Ti2SnC MAX phase for ultra-wideband electromagnetic
  wave absorption](https://doi.org/10.1002/cey2.638). *Carbon Energy, 6*,
  e638.
- Ferreira, A. F., da Silva, A. J., & de Castro, J. A. (2006). [Simulation of
  the solidification of pure nickel via the phase-field
  method](https://doi.org/10.1590/S1516-14392006000400002). *Materials
  Research, 9*, 349–356.
