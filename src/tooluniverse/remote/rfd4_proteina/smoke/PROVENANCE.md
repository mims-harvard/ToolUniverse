# Where `monomer.cif` came from

Byte-identical to `examples/monomer.cif` in
[nvidia/RFD4-Proteina](https://huggingface.co/nvidia/RFD4-Proteina) at the
revision this provider pins, `a06e2509c7033b010fc43614e9fd840303588502`.

    sha256  2211795f856d1df247b828ed2362d5508726fd19d8b6c661417630857f35b8e1
    size    3062 bytes

    curl -sL https://huggingface.co/nvidia/RFD4-Proteina/resolve/a06e2509c7033b010fc43614e9fd840303588502/examples/monomer.cif

BSD 3-Clause, Copyright (c) 2026 Institute for Protein Design, University of
Washington — the same licence as the model and weights.

## Why it is a copy rather than a fetch

STANDARD section 7 says third-party kits are referenced, never vendored, and
this file is the one place this provider does hold upstream bytes. The reason
is what a smoke is for: it must run as the fifth step of `tu remote setup`,
after weights and before anything has been served, and it must be the same
input every time so that a failure means the model changed rather than the
input did. Fetching it would make the smoke depend on the network a second
time, after the step whose job was to make the network unnecessary.

It is 3 KB of design specification, not code: a 100-residue unconditional
monomer with no input coordinates, which is the smallest thing that exercises
the whole design path. Nothing imports it and nothing executes it.

The digest above is what makes the copy checkable. If upstream changes the
example, this file does not silently follow — the digest stops matching and
that is a deliberate decision to make, not a drift to absorb.
