# Intel atomic deployment

The live preflight selected the wired Intel route at `192.168.8.186`; the
matching SSH alias is `blu-intel-lan` (`agar`, dedicated Intel key).

From the repository root on the Studio, atomically deploy the current adaptive
COMPLETE surface with exactly:

```sh
surface="lab/candidates/visual-presentation/generated-adaptive/intel/current.ansi"
blu-route --require-wired intel >/dev/null && \
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes blu-intel-lan \
  'umask 077; d=/Users/agar/.blu-ephemeral; mkdir -p "$d"; t="$d/current.ansi.$$"; cat >"$t" && mv -f "$t" "$d/current.ansi"' \
  < "$surface"
```

For a 120-second delayed view, use the same atomic deployment inside a bounded
background delay:

```sh
surface="lab/candidates/visual-presentation/generated-adaptive/intel/current.ansi"
blu-route --require-wired intel >/dev/null && \
( sleep 120; ssh -o BatchMode=yes -o StrictHostKeyChecking=yes blu-intel-lan \
  'umask 077; d=/Users/agar/.blu-ephemeral; mkdir -p "$d"; t="$d/current.ansi.$$"; cat >"$t" && mv -f "$t" "$d/current.ansi"' \
  < "$surface" ) >/dev/null 2>&1 &
```

The Intel-side display reads only `/Users/agar/.blu-ephemeral/current.ansi`.
Each deployment replaces that file; no rolling history or log is created.
