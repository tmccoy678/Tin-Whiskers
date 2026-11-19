# Official-source environment comparison

Snapshot date: 2026-11-19. Only official repositories and their documentation
were used.

## NASim — selected

- Official repository: <https://github.com/Jjschwartz/NetworkAttackSimulator>
- Pinned branch head used:
  <https://github.com/Jjschwartz/NetworkAttackSimulator/commit/4f26de37cfdc3e4553ed8b7484c4db8e2924bdea>
- Official installation guide:
  <https://github.com/Jjschwartz/NetworkAttackSimulator/blob/4f26de37cfdc3e4553ed8b7484c4db8e2924bdea/docs/source/tutorials/installation.rst>
- Official custom-scenario guide:
  <https://github.com/Jjschwartz/NetworkAttackSimulator/blob/4f26de37cfdc3e4553ed8b7484c4db8e2924bdea/docs/source/tutorials/creating_scenarios.rst>

The official README describes 0.12.0 as a stable release with bug-fix
maintenance and exposes Gymnasium environments. `setup.py` requires Python
3.8+, Gymnasium, NumPy, NetworkX, Matplotlib, PyYAML, and PrettyTable. The
candidate-local arm64 import/reset/step smoke test passed.

## CybORG / CAGE 4 — richer, heavier

- Official CybORG repository:
  <https://github.com/cage-challenge/CybORG>
- Official CAGE 4 repository:
  <https://github.com/cage-challenge/cage-challenge-4>
- CAGE 4 snapshot inspected:
  <https://github.com/cage-challenge/cage-challenge-4/commit/8c3c50ca54b176c2de199847944e8dcc035497e3>
- Official requirements:
  <https://github.com/cage-challenge/cage-challenge-4/blob/8c3c50ca54b176c2de199847944e8dcc035497e3/Requirements.txt>
- Official getting-started guide:
  <https://github.com/cage-challenge/cage-challenge-4/blob/8c3c50ca54b176c2de199847944e8dcc035497e3/documentation/docs/pages/tutorials/01_Getting_Started/2_Getting_Started.md>

CAGE 4 models blue defenders, red attackers, green users, and service impact.
Its official dependency set includes Ray/RLlib, PyTorch, PyTorch-Geometric,
PettingZoo, Stable Baselines, pygame, and networking utilities. That fidelity
is valuable for a later service-availability study; it is disproportionate for
the smallest native-Studio pilot.

## CyberBattleSim — current, Linux-oriented

- Official repository: <https://github.com/microsoft/CyberBattleSim>
- Snapshot inspected:
  <https://github.com/microsoft/CyberBattleSim/commit/aebf185ab0a7515f983ee696cb7b71d3fdcd107f>
- Official setup and environment description:
  <https://github.com/microsoft/CyberBattleSim/blob/aebf185ab0a7515f983ee696cb7b71d3fdcd107f/README.md>

CyberBattleSim provides abstract enterprise-network Gym environments and
baseline agents. Its official setup strongly recommends Linux or WSL and uses
an initialization path around a managed Python environment. That makes it less
direct than NASim for a native Apple-silicon candidate, even though its
repository is more recently active.

## Selection boundary

The decision is compatibility plus proportionality, not a claim that NASim is
universally best. NASim is best for this smallest reproducible synthetic
choice benchmark. CAGE 4 becomes the leading candidate when defender actions,
green-user traffic, and mutable service availability are required.
