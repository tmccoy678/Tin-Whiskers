# Preserved unfavorable runs

The final pilot is `results/pilot`. Three earlier bounded runs remain because
their failures changed the instrument:

| Directory | What changed next | Q evaluation outcome |
|---|---|---|
| `pilot-initial-sparse-failure` | Added small intermediate host values so progress before the final target is measurable. | 0/16 success on train and held-out. |
| `pilot-observation-q-failure` | Replaced last-observation-only state with cumulative successful Gym action results. | 0/16 success on train and held-out. |
| `pilot-120-belief-failure` | Increased training from 120 to 600 episodes while retaining the same final scenario and state definition. | 0/16 success on train and held-out. |

Each directory retains its manifest, summary, episode records, Q table, and
gzip-compressed exact step records. The final 600-episode pilot reached 16/16
on both evaluation scenarios; its training record still retains 545 failed
episodes.
