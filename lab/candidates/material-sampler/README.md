# Bounded-serendipity material sampler

This tool draws reproducible candidate settings from the validated material
manifests without editing them or executing a physical experiment.

Supported paths:

- Earth `exploratory`: samples only allow-listed `proposed` PEDOT geometry,
  ambient environment, waveform, and optical ranges.
- Space `screening`: samples only allow-listed `proposed` CBRAM coupon,
  vacuum-screen, and optical-interface ranges while retaining every
  `required-unset` mission gate.
- `promotion`: permitted structurally for either regime, but rejected whenever
  the source manifest contains a `required-unset` blocker. The current space
  manifest therefore emits a complete rejected draw and exits with status 2.

The sampler never creates a range around an `established` point. Established
quantities appear in the output as `fixed-established`; proposed hard stops and
admission thresholds not named as serendipity axes remain
`fixed-proposed-control`. Every draw includes all source quantities, the exact
source-manifest SHA-256, the policy SHA-256, admitted enum selections,
required-unset blockers, and rejected-combination reasons.

Examples:

```sh
python3 lab/candidates/material-sampler/sample.py \
  --regime earth --mode exploratory --seed 319

python3 lab/candidates/material-sampler/sample.py \
  --regime space --mode screening --seed 319

python3 lab/candidates/material-sampler/sample.py \
  --regime space --mode promotion --seed 319
```

Test with:

```sh
python3 -m unittest lab/candidates/material-sampler/test_sample.py
```

The JSON output is an auditable proposal, not a command to prepare chemicals,
energize hardware, enter a vacuum chamber, or expose anything to radiation. It
adds no material-performance or space-reliability claim.
