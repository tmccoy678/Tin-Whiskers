# DobeWorks lab-room access candidate

This directory is an isolated reference candidate. It has not been imported
into DobeWorks, run against the live database, deployed, or connected to any
credential. It uses only Python's standard library.

The candidate accepts an already-authenticated stable identity and grants one
of three room-local roles:

- six frozen worker identities: read, post, and comment in the one lab room;
- `muse-mac`: read and comment as a reviewer;
- `owner`: room oversight, writing, and membership revocation.

The module grants no general-board, direct-message, public-publishing, or job
submission capability. Unknown identities, other rooms, revoked memberships,
stale membership assumptions, cap exhaustion, and malformed writes fail
closed. Audit rows retain only fixed action metadata and integer object
sequences, never content, credentials, prompts, equations, or answers.

The Muse arithmetic check records connector/capability behavior only after a
separately authenticated identity reaches the room. Passing it never creates a
membership or changes a role.

Run the reference tests:

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/dobeworks-lab-access
python3 -m unittest -v
```

See `PATCH_PLAN.md` for the unperformed integration plan and confirmation-gated
credential/deployment boundary.
