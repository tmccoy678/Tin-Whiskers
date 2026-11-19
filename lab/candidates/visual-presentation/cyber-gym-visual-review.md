# Cyber-gym Q-lattice human-eye review

## Verdict

The existing HTML is a **go for expert inspection of the action-value sweep**
and a **no-go as a self-explanatory rolling terminal**.

At laptop distance, green/red value direction and the yellow chosen-cell outline
are immediate. Phase, scenario, policy, step, and reward are readable. The first
viewport shows only actions `a0` through `a8`; action meanings are available
only as hover titles, the chosen action is not named, reversal state is absent
from the table, and units are explained only in the paragraph. A friend can see
that values sweep and a cell wins, but cannot identify the chosen operation,
target, reversal state, or row units without narration.

## Smallest HTML changes

1. Add visible left columns for `episode`, `reversal before`, `chosen action`
   (`aN Kind[target]`), `chosen Q`, and `units`.
2. Keep phase/scenario/policy and those new columns sticky at the left while the
   18 action columns scroll.
3. Replace bare `a0…a17` header text with a two-line short form such as
   `a04 Exploit@1`; retain the full hover title.
4. Add `raw reward` or `reward/50` beside each policy name. Preserve the current
   instruction to compare rank within a policy rather than magnitude across
   policies.
5. Preserve the yellow outline and add a small `CHOSEN` text badge so selection
   does not depend on color or border perception alone.

These are label and sticky-column changes only. The benchmark values, action
ranking, policy, episodes, and scenarios remain untouched.

## Intel delayed view

`cyber_q_intel_snapshot.swift` reads the existing TSV/action map and atomically
writes one current ANSI frame. The generated example is
`generated-adaptive/intel/cyber-q-current.ansi` for
`eval-adapt / reversal-deception / neural-q / episode 0`, final step 24. It
shows:

- `CLASSICAL Q VALUES · NOT QUANTUM`;
- phase, scenario, policy, episode, step, and reversal state;
- explicit `reward/50` units;
- chosen and runner-up action kind/target, values, and margin;
- all 18 Q values in three compact rows;
- one clear/home surface with `NO HISTORY`.

Deploy it with the 120-second command in
`generated-adaptive/INTEL-DEPLOYMENT.md` after setting `surface` to the cyber-Q
ANSI path. The cyber benchmark files remain unchanged.
