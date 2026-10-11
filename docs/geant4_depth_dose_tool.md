# GEANT4 depth-dose simulation

`geant4_depth_dose_simulation` runs one Monte Carlo simulation with GEANT4: a beam of identical particles is fired into a slab of a single NIST material, and the energy deposited in each equal depth bin comes back as numbers. It answers range and shielding questions — where a therapeutic proton beam stops in tissue, how much of a gamma beam a lead slab absorbs, how an ion's range shifts with energy or material.

## What varies, and what does not

Only `particle`, `energy_mev`, `material`, `thickness_cm`, `bins`, `events` and `timeout_seconds` vary. The geometry, the physics list (`QBBC`) and the scoring are fixed in `src/tooluniverse/data/geant4/depth_dose.cc`, which ships with the package. The tool accepts no geometry description, no macro and no physics configuration, because each of those is a way to run arbitrary code inside the simulation process. `material` and `particle` are closed lists checked before anything is executed; every number has a declared range and is rejected outside it.

The beam starts 1 cm in front of the target, travels along +z, and the target is divided into `bins` equal slices by a GEANT4 replica, each of which scores the energy deposited in it.

## Requirements

A local GEANT4 with its physics data. The tool finds it through `geant4-config` on `PATH`, or `GEANT4_CONFIG` pointing at that program. No root access is needed:

```bash
micromamba create -p ~/geant4-env -c conda-forge geant4
export PATH=$HOME/geant4-env/bin:$PATH
```

On first use the application is compiled against that installation with `c++` (or `$CXX`) and cached in `~/.tooluniverse/geant4`, keyed by a hash of the source and the toolkit version, so upgrading GEANT4 rebuilds instead of silently reusing a stale binary. Set `TOOLUNIVERSE_GEANT4_CACHE` to move the cache. Compilation takes a few seconds once; later calls start immediately.

GEANT4 reads its physics data from a set of `G4*DATA` environment variables. Any that are already exported are left alone. For the rest the tool asks `geant4-config --datasets` and checks that each directory exists — packaged builds do not always install the data where the toolkit was built expecting it, and conda-forge in particular installs `ENSDFSTATE3.0` where the toolkit asks for `G4ENSDFSTATE3.0`, which otherwise aborts the run at startup with `ENSDFSTATE.dat is not found`. When the advertised path is missing, the tool looks for the directory beside it that differs only by that `G4` prefix.

## Output

```json
{
  "status": "success",
  "data": {
    "material": "G4_WATER",
    "particle": "proton",
    "energy_mev": 150.0,
    "events": 100,
    "thickness_cm": 20.0,
    "bin_width_cm": 0.1,
    "total_edep_mev": 14314.97,
    "edep_mev_per_bin": [12.9, 13.1, "..."],
    "geant4_version": "11.4.3",
    "summary": {
      "peak_bin": 158,
      "peak_depth_cm": 15.85,
      "peak_edep_mev": 300.86,
      "last_depth_with_dose_cm": 19.8,
      "edep_mev_per_event": 143.15
    }
  }
}
```

`edep_mev_per_bin` is the raw curve, in MeV summed over all events; divide by `events` for per-particle numbers, and by the slice mass for dose. `summary.peak_depth_cm` is the centre of the heaviest bin — the Bragg peak for ions. `last_depth_with_dose_cm` extends past the peak because secondary neutrons and gammas keep depositing beyond where the primaries stop.

## Measured accuracy

Protons in water, 1 mm bins, compared with the ICRU 49 / PSTAR CSDA range:

| Energy | Peak depth here | Published range |
|---|---|---|
| 100 MeV | 7.65 cm | 7.72 cm |
| 150 MeV | 15.85 cm | 15.77 cm |
| 200 MeV | 26.05 cm | 25.96 cm |

Each of those runs took one to three seconds for a few hundred events on one CPU core. Statistical noise is what sets the error at low event counts: a few hundred events put the peak within a bin or two, while a smooth curve for publication wants tens of thousands.

## Choosing the numbers

`thickness_cm` must exceed the expected range, or the beam leaves the target before stopping and there is no peak to find — the curve simply ends. `bins` sets the depth resolution as `thickness_cm / bins`; a resolution much finer than the scatter in the beam only adds noise. `events` costs time roughly linearly.

## Errors

A missing installation says so and names what to install, rather than failing as though the tool were broken. An out-of-range or unknown argument is rejected before the simulation starts, naming the argument and its range. A run that exceeds `timeout_seconds` says which of events, bins or the timeout to change. A GEANT4 abort for unreadable physics data is reported as that, with the variables it could not resolve.
