# Grover comparator decision

The frozen gym does not contain a valid opaque-search subproblem.

Grover search requires a Boolean oracle over `N` candidates with a declared
marked-set cardinality, and oracle calls—not simulator steps or wall time—must
be the resource being compared. This NASim scenario instead supplies:

- labeled action kinds and targets;
- structured preconditions and sequential state transitions;
- stochastic exploit outcomes;
- more than one potentially useful action at a state;
- delayed reward requiring a sequence of actions.

Defining an oracle as "does this action eventually win?" would require hidden
simulator rollouts or a solved value function. Treating that operation as a
single phase-oracle call would hide the principal computation inside the oracle
and create the claimed query advantage by definition.

A future comparator becomes valid only if the gym introduces a separate frozen
decision whose API exposes an opaque Boolean function with a known marked-set
promise. That comparator must then report:

1. one count for each classical Boolean-oracle evaluation;
2. one count for each Grover phase-oracle application;
3. state-preparation and diffusion costs separately;
4. all marked items, seeds, and iteration budgets;
5. held-out marked items and the overshoot curve;
6. the explicit statement that matching output from a classical state-vector
   simulator is not physical quantum behavior or hardware speedup.

No such oracle was fabricated for this pilot.
