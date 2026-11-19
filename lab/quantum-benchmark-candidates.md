# Quantum benchmark candidates

These are small comparison tasks with a primary-source quantum result and a
classical baseline that can run locally. Matching their outputs is evidence of
task matching only. A classical emulator can reproduce small quantum
distributions without implementing the physical quantum mechanism.

## 1. CHSH nonlocal game

| Field | Candidate |
|---|---|
| Task I/O | Two separated parties receive independent uniform bits `x,y` and return bits `a,b`; win when `a XOR b = x AND y`. |
| Resource metric | Win probability, or equivalently `S = E00 + E01 + E10 - E11`, with trial count and input independence recorded. |
| Classical baseline and limit | Enumerate the 16 deterministic local response pairs and their mixtures. With no communication and measurement-independent inputs, `P(win) <= 3/4` and `S <= 2`. |
| Quantum result | A Bell pair with measurement angles separated by `pi/4` reaches `P(win) = cos^2(pi/8) ~= 0.853553` and `S = 2 sqrt(2)`. The realizable inequality is the primary CHSH result: [Clauser, Horne, Shimony, and Holt (1969)](https://doi.org/10.1103/PhysRevLett.23.880). |
| Small run | Enumerate the classical strategies exactly, then Monte Carlo the local bound and ideal/noisy two-qubit distributions for `10^5` seeded trials. |
| Distinguishing perturbation | Choose `x,y` after pair preparation, randomly rotate one measurement basis, and retain the full conditional table `P(a,b|x,y)`. A fixed answer table or shared schedule loses the violation. Software that sees both inputs can still simulate the table, so a matching local program is not evidence of physical nonlocality. |

## 2. Grover unstructured search

| Field | Candidate |
|---|---|
| Task I/O | Input is opaque oracle access to `f:{0,...,N-1}->{0,1}` with exactly one marked index; output is that index. Draw a fresh marked index every trial. |
| Resource metric | Oracle calls needed for a preregistered success probability, reported against `N`; wall time is secondary because implementations differ. |
| Classical baseline and limit | Query indices in a seeded random permutation. Classical deterministic or randomized black-box search needs `Theta(N)` queries; Grover's primary paper states that 50% success needs at least `N/2` classical examinations. |
| Quantum result | Amplitude amplification obtains the marked item in `O(sqrt(N))` oracle steps, with ideal success after `q` iterations `sin^2((2q+1) asin(1/sqrt(N)))`: [Grover (1996)](https://doi.org/10.1145/237814.237866), [open primary manuscript](https://arxiv.org/abs/quant-ph/9605043). |
| Small run | Use `N = 16, 64, 256, 1024`; run the classical permutation baseline and a state-vector implementation across all marked indices and several query budgets. |
| Distinguishing perturbation | Sweep iteration count through the optimum and beyond it, rerandomize the marked item, and replace the oracle phase `pi` with a concealed offset on held-out trials. The expected amplification/overshoot curve tests the algorithm rather than a memorized answer. A classical state-vector simulator can match that curve, so the curve alone does not establish quantum hardware or speedup. |

## 3. Hong-Ou-Mandel two-photon interference

| Field | Candidate |
|---|---|
| Task I/O | Send one photon into each input of a 50:50 beam splitter; input controls are relative delay and polarization overlap; output is the number of coincidence and same-port detections. |
| Resource metric | Coincidence probability and dip visibility versus independently calibrated wave-packet overlap, with detected-pair count and loss reported. |
| Classical baseline and limit | A seeded independent distinguishable-particle beam-splitter Monte Carlo gives coincidence probability `1/2`. It is the declared classical baseline, not a universal model of classical optical fields. |
| Quantum result | For an ideal two-single-photon input, bosonic interference gives `P(coincidence) = (1 - |<psi1|psi2>|^2)/2`, reaching zero for indistinguishable photons. The original fourth-order interference experiment is [Hong, Ou, and Mandel (1987)](https://doi.org/10.1103/PhysRevLett.59.2044). |
| Small run | Simulate `10^5` seeded photon pairs over overlap values `0, 0.25, 0.5, 0.75, 1`; preserve all three number outcomes rather than only a rendered dip. |
| Distinguishing perturbation | Independently sweep delay and polarization, then change beam-splitter reflectivity. A zero inserted only at nominal overlap fails the full overlap and number-output surface. A classical program can nevertheless sample the same formula, so matching counts do not prove that its substrate is quantum. |

## Admission rule

Promote a benchmark only with the oracle or optical interface frozen, the
classical comparator run under the same declared input distribution, every
seed retained, and the perturbation evaluated on held-out trials. Report
hardware quantum behavior only when the physical assumptions required by the
bound are independently enforced; otherwise report simulation or task-level
agreement.
