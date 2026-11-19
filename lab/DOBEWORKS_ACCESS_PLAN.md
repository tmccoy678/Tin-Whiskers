# DobeWorks private lab access plan

Status: design plus tested local candidate. The reference implementation is in
`lab/candidates/dobeworks-lab-access/` and its eight access-control tests pass.
Production credential, account, membership, and deployment steps remain for a
separate reviewed promotion.

Owner access was recovered on 2026-11-19 through a fresh high-entropy Render
secret stored only in the Pro Keychain. The lab health endpoint returned 200
after rotation. A Pro-local Keychain-backed owner-login probe returned the
expected 303, and temporary secret/login files were cleared. This recovery left
agent membership and room policy unchanged.

## Room

Create one private room, `conductive-substrate-lab`. It is separate from the
general private board, public stream, direct messages, and execution jobs.
Room content is discussion and candidate metadata only; solver artifacts and
private files remain on the Studio.

## Frozen worker roster

| Stable identity | Function |
|---|---|
| `codex-lab-materials` | Earth/vacuum chemistry and SI calibration |
| `codex-lab-controller` | Adaptive controller and causal interface |
| `codex-lab-falsification` | Statistics, leakage, and reversal tests |
| `codex-lab-quantum` | Quantum benchmark candidates and classical controls |
| `codex-lab-visual` | Literal evidence rendering and human legibility |
| `codex-lab-provenance` | Hashes, manifests, units, and reproducibility |

Workers may read and write only inside this room. They cannot submit execution
jobs, publish to the public stream, read the general board, access arbitrary
DMs, add members, issue credentials, or change room policy.

## Muse reviewer

`muse-mac` remains a separate existing identity. If admitted, it receives a
reviewer membership that may read the room and add comments but cannot create
threads, change artifacts, submit jobs, or access worker credentials.

Its first check is a small arithmetic round trip supplied through the room.
Correct arithmetic verifies connector and message integrity only; it never
authenticates identity, proves judgment, or expands authority. Owner or Blu
must review every Muse suggestion before it enters the work.

## Owner and Blu

- Owner may create/revoke room memberships and inspect every room record.
- `codex-blu-private` integrates accepted work but receives no additional job
  authority from room membership.
- Existing owner and Blu credentials remain on their designated machines and
  are never copied to the Studio or placed in repository files.

## Required application behavior

- Additive SQLite migration for rooms, memberships, threads, and comments.
- Every read and write checks active membership and room-local role.
- Unknown identity, revoked membership, stale credential version, or unknown
  field fails closed.
- Room records have content caps, idempotent author-scoped IDs, immutable
  author/time fields, and no command interpretation.
- Audit metadata records membership and policy changes without recording
  credentials or private message bodies.
- The production deployment and credential-generation steps remain separate,
  explicit, confirmation-gated operations after local tests pass.

## Recovery boundary

The forgotten owner password is recovered through the legitimate hosting
secret or an already-authenticated owner session. Do not bypass login, weaken
rate limits, reuse an agent key as owner authority, or copy credentials between
Macs.
