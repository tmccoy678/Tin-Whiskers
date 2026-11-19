# First MOOSE voltage-routing result

MOOSE solved `div(sigma * grad(V)) = 0` on three initial image-derived topologies and one developed follow-up with identical one-volt source and sink boundaries. Metal conductivity was normalized to `1`; surrounding-medium conductivity was `1e-6`. Each topology included identical three-pixel terminal bus bars. The cut removed one seven-by-seven-pixel region nearest the interconnect center.

| Topology | Interconnect fraction | Terminal flux | Flux / interconnect | Flux after cut | Retained |
|---|---:|---:|---:|---:|---:|
| Straight wire | 0.004720 | 0.015862 | 3.360455 | 2.9417e-06 | 0.019% |
| Parallel grid | 0.065267 | 0.079305 | 1.215085 | 6.3447e-02 | 80.004% |
| Grown Cherenkov | 0.014893 | 0.004137 | 0.277805 | 4.1524e-06 | 0.100% |
| Recurrently developed | 0.049778 | 0.004095 | 0.082262 | 4.0938e-03 | 99.975% |

The straight wire delivered the greatest conductance per unit interconnect and lost its path under one cut. The five-rail grid delivered the greatest absolute terminal flux and retained 80% after the cut. The first grown Cherenkov topology delivered the least conductance per unit interconnect and lost its path under the cut.

After recurrent cut-and-regrow epochs, the developed topology retained essentially all of its MOOSE terminal flux under the practiced local cut while using less interconnect area than the grid. Its absolute flux and conductance per unit material remained far below the grid. Repeated injury earned location-specific redundancy; the next developmental pressure must reward delivered current and useful capacity across multiple terminal configurations.
