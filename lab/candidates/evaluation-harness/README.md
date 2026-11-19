# Evaluation-record candidate

This isolated, standard-library Python candidate turns the falsification memo's
record structure into a fail-closed contract. It does not run a solver, change
canonical results, or perform inferential statistics.

## Enforced record rules

- exact schemas for `design.tsv`, `events.tsv`, `samples.tsv`, and
  `unit-summary.tsv`;
- one `W`, `G`, `F24`, `F36`, `A`, and `Y` row per block;
- identical within-block budgets, material, lesion algorithm, and schedule
  hash;
- globally unique microstate seeds and policy, growth, and damage RNG stream
  identifiers;
- frozen, distinct `F24` and `F36` provenance hashes;
- exact ordered `A/Y` timestamps, command hashes, and cumulative actuator
  energy;
- explicit containment state/code and validity/exclusion-code pairs;
- recomputation of safe useful-service fraction `U`; and
- descriptive paired `A-Y` and `A-best-fixed` contrasts from complete valid
  blocks.

`samples.tsv` adds `dt_s`, `episode`, and `containment_code` to the bench memo's
minimum columns. They remove ambiguity from time weighting, terminal-event
scoring, and containment interpretation.

The values under `inference` in `config.json` are configuration only. The tool
always emits `"inference": "not_run"`; it does not manufacture bootstrap
intervals, sequential results, power claims, or evidence from the fixture.

## Commands

From this directory:

```sh
python3 evaluation_harness.py validate tests/fixtures/valid
python3 evaluation_harness.py summarize tests/fixtures/valid
python3 -m unittest discover -s tests -v
```

An alternate configuration goes before the subcommand:

```sh
python3 evaluation_harness.py --config config.json validate tests/fixtures/valid
```

Validation failures return exit status `2` with one `INVALID:` message on
standard error. `summarize` validates first and prints exact decimals as JSON
strings.

## Candidate boundary

The physical safety limits in `config.json` are synthetic fixture values, not
material claims. A promoted harness must receive calibrated limits and frozen
controller/action schemas before evaluation.
