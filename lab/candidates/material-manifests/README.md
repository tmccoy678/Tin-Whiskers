# Candidate material manifests

These files are machine-readable candidates, not canonical experiment inputs.
They preserve the two calibration regimes as separate admission paths:

- `earth-pedot.json`: aqueous PEDOT:PSS proof of principle at ambient pressure.
- `space-cbram.json`: capped solid-state Ag/Ge-Se/Ni vacuum and reliability coupon.

`schema.json` defines the shared quantity contract. Every experimental number
in a manifest is an object containing:

- `value` and `unit`;
- `status`: `established`, `proposed`, or `required-unset`;
- a direct source or an engineering rationale;
- an inclusive allowable range; and
- a hard-stop condition/action when crossing the value can damage the specimen,
  invalidate the comparison, or overstate admission.

Raw numeric leaves are forbidden. A `required-unset` quantity must have a null
value, null range bounds, and a hard stop that blocks promotion. The space
manifest therefore cannot be promoted until mission TID, SEE, displacement
damage, lifetime, shielding, and operational temperature inputs are supplied.
The proposed cobalt-60 screen is retained as a materials experiment and is not
silently promoted into a mission requirement.

The dependency-free validator enforces these semantic rules in addition to the
documented JSON Schema:

```sh
python3 lab/candidates/material-manifests/validate.py
python3 -m unittest lab/candidates/material-manifests/test_validate.py
```

The validator deliberately does not merge, translate, or copy numbers between
the Earth and space manifests. A later integrator may promote a passing
candidate only through the named gates and the repository's lab admission rule.
