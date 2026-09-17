# Raw vs. calculated/derived data

Getting this split right is the entire point of ASM-style structuring — a
LIMS or downstream analyst needs to know which numbers came straight off the
detector and which were computed (and from what).

## Rule of thumb

- **Raw measurement** — a value that is one hop from the physical detector:
  absorbance, fluorescence intensity, raw Ct/Cq cycle number, raw peak area,
  cell count from the imaging sensor, raw optical density.
- **Calculated/derived value** — anything the instrument's own software (or
  a downstream formula) computed FROM one or more raw measurements: a
  concentration derived from a standard curve, a ratio of two channels, a
  percentage, a fold-change, an index.

If you can't tell which a column is, classify it as `raw_measurements` and
leave a `null`/absent data-source link rather than guessing it is calculated
— an unlinked "calculated" value with no traceability is worse than an
under-classified raw one.

## Common calculated fields by instrument type

| Instrument type      | Typical calculated fields                                  | Typically derived from |
|-----------------------|--------------------------------------------------------------|-------------------------|
| Spectrophotometer (e.g. NanoDrop) | Concentration (ng/µL), 260/280 ratio, 260/230 ratio | Absorbance at 260/280/230 nm |
| Plate reader (colorimetric/fluorescent) | Concentration from standard curve, %CV, blank-corrected signal | Raw absorbance/fluorescence per well |
| Cell counter (e.g. Vi-CELL) | Viability %, dilution-adjusted cell density | Live/total cell counts from imaging |
| qPCR | Relative quantity (ΔΔCt), fold change, efficiency-corrected quantity | Raw Ct/Cq values |
| Electrophoresis (e.g. TapeStation) | DIN/RIN (integrity number), region % concentration, average fragment size | Raw trace intensity vs. migration time |
| Chromatography (HPLC/UPLC) | Peak purity %, retention-time-normalized area, quantified concentration vs. calibration curve | Raw peak area/height |
| ELISA reader | Concentration from 4-parameter logistic standard curve | Raw OD per well |

## Column-name heuristics used by the Tier 2 fallback parser

The fallback parser flags a column as *likely calculated* (never asserts it
outright) when its header matches patterns like:

- `conc`, `concentration`, `%`, `percent`, `ratio`, `cv`, `fold`, `rq`,
  `delta`, `normalized`, `corrected`, `purity`, `viability`, `din`, `rin`

and as *likely raw* when it matches:

- `abs`, `absorbance`, `od`, `fluor`, `intensity`, `ct`, `cq`, `count`,
  `area`, `height`, `signal`, `raw`

A column matching neither pattern is treated as raw by default (the safer
default — raw values need no traceability link, calculated ones do).
