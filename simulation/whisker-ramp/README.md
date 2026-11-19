# Documented whisker failure boundary

## Real cases

### Persistent low-current bridge

NASA documents a power-utility circuit that entered service around 1983 and
failed around 2002 when a tin whisker bridged adjacent leads on a standard
through-hole DIP integrated circuit. The copper leads had pure matte-tin
plating, the lead spacing was approximately `0.75–1.0 mm`, the IC had at most
`10 V` available, and the permanent short carried too little current to fuse
the whisker.

Source: [NASA GSFC, *20 Years to
Failure*](https://nepp.nasa.gov/whisker/anecdote/20year/).

### Self-erasing 48-volt bridge

A Westinghouse technical case describes a `48 V` power supply whose output
breaker tripped when whiskers apparently bridged the cases of two tin-plated
potentiometers. The short actuated the overvoltage trip and vaporized the small
whisker, removing the immediate fault evidence.

Source: [NASA review of documented whisker
failures](https://nepp.nasa.gov/whisker/reference/tech_papers/2006-Leidecker-Tin-Whisker-Failures.pdf),
pp. 18–19.

### Sustained metal-vapor arc

NASA reports a thermal-vacuum event in which zinc whiskers bridged a `45 mil`
gap between a plated bus rail and aluminum chassis. The metal-vapor arc lasted
`4.7 s`; `20 A` fuse pairs opened on eleven boards, and the event melted most
of the rail and part of the housing. NASA's general whisker guidance places the
vacuum arc regime above roughly `18 V` with a supply capable of several amps;
the resulting metal plasma can conduct hundreds of amperes.

## Measured solid-whisker envelope

NASA reports measured fusing capacities up to approximately:

| Diameter | Fusing current |
|---:|---:|
| `1 µm` | `10 mA` |
| `2.5 µm` | `30 mA` |
| `4 µm` | `75 mA` |

The voltage-ramp script fits a power law only to these three points, combines
it with a `0.875 mm` cylindrical tin path and circuit series impedance, and
solves the diameter required to remain at 80% of the fitted fusing envelope.
Diameters beyond `4 µm` are explicit extrapolations for later multiphysics
testing.

Source: Courey, K. J. (2013). [*Risk of Tin Whiskers in D-subminiature
Connectors*](https://ntrs.nasa.gov/api/citations/20130012566/downloads/20130012566.pdf).

## Run

```sh
Rscript ramp.R
```

The output separates stable solid conduction, solid-path fusion, and a
potential metal-vapor-arc regime. It never treats plasma as a thicker whisker.
