# Space-processor and terrestrial-control comparison

Status: primary-source architecture screen for the adaptive conductive
substrate program.

## Representative flight processors

| Processor | Compute and scale | Power and interconnect | Radiation, error handling, and redundancy |
|---|---|---|---|
| **BAE RAD750** | 200 MHz, more than 400 Dhrystone 2.1 MIPS; 0.15 µm radiation-hardened bulk CMOS | Component sheet emphasizes a compact single-core control processor | 1 Mrad(Si) total-dose rating, less than `1.6e-10` SEU/bit-day at the stated GEO condition, latchup immune ([BAE datasheet](https://www.baesystems.com/en/dam/jcr%3Ac297f318-c618-4015-9399-adf76ac5cf55/16-f78-RAD750-Component-datasheet-2025-web.2025-06-25-21-57-42.pdf)) |
| **Frontgrade GR740** | Four fault-tolerant LEON4 SPARC V8 cores at 250 MHz; more than 1,700 DMIPS | Less than 2 W at 40 °C; eight 300 Mbit/s SpaceWire links, two Gigabit Ethernet MACs, PCI; 29 × 29 mm flight package | 300 krad(Si), SEL LET above 125 MeV·cm²/mg; fault-tolerant register/cache RAM, Reed–Solomon SDRAM interface, EDAC PROM/I/O, watchdogs, qualified standby boot path ([GR740 overview](https://download.gaisler.com/products/gr740/doc/GR740-OVERVIEW.pdf), [product page](https://www.gaisler.com/products/gr740)) |
| **BAE RAD5545 family** | Four RAD5500 Power Architecture cores; up to 5.6 GOPS and 3.7 GFLOPS | Up to 102 Gb/s memory and 64 Gb/s I/O throughput; SBC provides four 10 GB/s Serial RapidIO ports and twelve SpaceWire links up to 320 Mbit/s | Radiation-hardened SoC; 4 GB ECC DRAM and 1 GB triple-modular-redundant flash on the SDR platform ([BAE architecture](https://marketing.us.baesystems.com/interactives/spacetech/index.html), [SBC/SDR sheet](https://www.baesystems.com/en-us/dam/jcr%3A76bd3e43-0c31-481e-8e69-ddbf6f29a43d/20-a39-SpaceVPX-SDR-datasheet-8.5x11-2025-web.pdf)) |
| **NASA/Microchip PIC64-HPSC** | Eight 64-bit RISC-V application cores with vector engines; NASA target exceeds current space processors by more than 100×; GlobalFoundries 12 nm LP+ | User-controlled power islands; integrated 240 Gb/s time-sensitive Ethernet/RDMA switch, 16 lanes PCIe Gen3, CXL 2.0; multiple HPSC devices can form larger coherent systems | Rad-hard-by-design, cache-coherent fault-tolerant SoC; PIC64-HPSC1000-RH specifies 100 krad(Si), tested to 200 krad, and 78 MeV·cm²/mg SEL. Early SEE tests reported zero uncorrected errors and zero external resets in the completed campaign ([NASA HPSC](https://www.nasa.gov/game-changing-development-projects/high-performance-spaceflight-computing-hpsc/), [NASA TechPort](https://techport.nasa.gov/projects/13569), [Microchip product](https://www.microchip.com/en-us/products/microprocessors/64-bit-mpus/pic64-hpsc), [radiation milestone](https://www.microchip.com/en-us/about/news-releases/products/microchip-achieves-key-program-milestones-for-pic64-hpsc-spaceflight-computing-series)) |

HPSC is the clearest contemporary bridge: leading-edge-enough 12 nm fabrication,
vector compute, granular power control, fault tolerance, and a 240 Gb/s network
share one flight architecture. Its 100× target is a system-capability ratio;
NASA's current program is measuring power, performance, reliability, and
radiation tolerance on manufactured silicon.

## Contemporary terrestrial controls

| Processor | Compute and scale | Power and interconnect | Error and repair strategy |
|---|---|---|---|
| **AMD EPYC 9965 / Embedded 9005 class** | Up to 192 Zen 5c cores / 384 threads, 2.25 GHz base and 3.70 GHz boost; 3 nm dense cores with 6 nm I/O die | 500 W TDP; 12 DDR5 channels, up to 6 TB at 2DPC in the server sheet, 160 PCIe Gen5 lanes in 2P configurations | ECC memory, Advanced Memory Device Correction, Dynamic Post-Package Repair for faulty DIMMs, machine-check/crash-dump and out-of-band error polling ([AMD datasheet](https://www.amd.com/content/dam/amd/en/documents/epyc-business-docs/datasheets/amd-epyc-9005-series-processor-datasheet.pdf), [embedded brief](https://www.amd.com/content/dam/amd/en/documents/products/embedded/epyc/epyc-embedded-9005-series-product-brief.pdf)) |
| **NVIDIA Blackwell Ultra / B200 class** | 208 billion transistors on TSMC 4NP; dual reticle dies act as one GPU; Blackwell Ultra reaches 15 PFLOPS dense NVFP4 | Up to 1 kW per B200 GPU; 288 GB HBM3E and up to 8 TB/s on Ultra, 10 TB/s die-to-die NV-HBI, 1.8 TB/s NVLink | Full coherence across dies, partitioning through MIG, confidential-computing paths, and predictive RAS at system scale ([NVIDIA architecture](https://www.nvidia.com/en-us/data-center/technologies/blackwell-architecture/), [Blackwell Ultra](https://developer.nvidia.com/blog/inside-nvidia-blackwell-ultra-the-chip-powering-the-ai-factory-era), [HGX B200 specifications](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html)) |
| **Intel Xeon 6 P-core class** | Up to 128 cores and 504 MB L3; AVX-512 and AMX deliver up to 2,048 INT8 operations/cycle/core | Up to 500 W; DDR5-6400 and MRDIMM up to 8,800 MT/s; CXL and integrated accelerators | ECC, persistent-fault detection, adaptive double-device correction, link CRC/retry, runtime soft PPR, boot-time hard PPR, error logging, and BMC RAS offload ([Intel product brief](https://www.intel.com/content/www/us/en/products/docs/xeon-6-product-brief.html), [Xeon 6 RAS paper](https://cdrdv2-public.intel.com/913303/AI-Ready-RAS-features-of-Intel-Xeon-6.pdf)) |

## Directly useful measures for the adaptive substrate

The completed seed-319 and seed-571 screens average `9,748.159` fully audited
choices per second. Each choice updates a `16 × 8` field, producing about
**1.248 million primary cell updates per second**, while also executing the
controller, renewal logic, budgets, reinforcement ledger, and approximately
`2.48 kB` of audit. The full seed-319 audit sustained about **24.2 MB/s** of
evidence output.

The processor controls define six measurable axes:

1. **Useful work rate:** choices/s, cell updates/s, delivered-current change,
   and renewal latency rather than a single primitive-operation count.
2. **Energy:** choices/J and delivered-current improvement/J. GR740 demonstrates
   a flight-qualified sub-2-W reference; HPSC demonstrates dynamic power islands;
   EPYC and B200 define 500–1,000-W high-throughput controls.
3. **Interconnect:** useful field delivery per link width and per unit area.
   Public controls span 300 Mbit/s SpaceWire through 240 Gb/s HPSC Ethernet to
   10 TB/s Blackwell die-to-die fabric.
4. **Radiation resilience:** safe service versus TID, LET, and upset injection,
   with time-to-detection, time-to-renewal, and retained function reported
   alongside raw error count.
5. **Repair:** ECC, TMR, spare lanes, Dynamic PPR, reboot, and module replacement
   become fixed comparators for path widening, dissolution, rerouting, and
   regrowth while service continues.
6. **Scale:** conductor feature size, active area, reservoir mass, and useful
   work per cubic millimeter connect the current reduced field to 150 nm RAD750,
   12 nm HPSC, and 3–4 nm terrestrial controls.

## Strongest positive research leads

- **Live topology repair is the distinctive target.** Current processors excel
  at detecting, correcting, isolating, and replacing faults. A developing
  conductor can add the complementary ability to change the physical route
  carrying service.
- **HPSC supplies the best first system comparator.** Its power islands,
  fault-tolerant multicore design, RDMA/TSN network, and scalable device fabric
  translate directly into bounded actuator regions, renewal domains, and
  multiple-substrate experiments.
- **Dynamic PPR supplies an elegant fixed repair control.** Compare a mapped-out
  failed memory region with a substrate that recruits material and re-establishes
  a route under the same fault schedule.
- **Interconnect is a first-class phenotype.** Measure bandwidth, latency,
  current concentration, heat, and repair together; every architecture above
  reveals that computation becomes valuable only when data and energy can move.
- **Radiation can become a developmental stimulus.** Controlled upset and dose
  schedules can test whether consequence-sensitive renewal preserves service,
  establishing a measurable bridge from software adaptation to material
  resilience.
