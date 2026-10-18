# Figure source and interpretation

The data figure asks whether the M48L-minus-parent conditional pH term is
robust to preparation and free-reference choice. It is a single-axis paired
sensitivity comparison, not a binding-performance estimate.

`paired_deltas.csv` contains all 33 matched reference combinations from the
native preparation pilot: three structural families, each with ten independent
free-reference combinations and one same-coordinate reference. Every comparison
uses the same bound sample before/after preparation; RoseTTAFold3 uses sample 0.
`reference_sensitivity.csv` retains the minimum and maximum of each of the six
family/reference groups before and after preparation. No rows were removed
within this pilot. Other RoseTTAFold3 bound samples were outside the native
re-preparation pilot and are not mixed into its before/after comparisons.

Each independent-reference group combines five own free-binder samples and two
same-family apo-receptor references. These combinations share inputs. Their
extrema are sensitivity ranges, not confidence intervals, biological replicates,
thermodynamic populations or independent model calls. Same-coordinate points
are single reference comparisons. Values are full 174-group protein-only PROPKA
independent-site linkage terms at 298.15 K, pH 6.0 minus 7.4; differences are
M48L minus parent. Positive values mean a larger conditional release-direction
contribution. Neither sign establishes affinity or measured pH selectivity.

The public CSVs contain aggregates and paired deltas, not candidate sequences,
coordinates, raw model payloads, credentials or machine metadata.

`render_figures.py` recreates both figures using Python/Matplotlib. SVG text is
editable; PDF and 300-dpi PNG exports are supplied. The web-blog widths are
intentionally wider than journal column defaults; TIFF/600-dpi manuscript
requirements do not apply. The workflow figure is conceptual, with skills and
tools both inside ToolUniverse; it makes no claim that every supported model was
run or every endpoint is biologically validated.

Final rendered checks: both PDFs have no text below 5 pt and no detected
text/stroke collisions (data figure minimum 8 pt; workflow minimum 9 pt).
Both are single-axis figures, so comparable-panel alignment is not applicable;
the alignment manifests record that scope. All labels, extrema and zero-line
positions were also inspected visually at the exported size. The workflow's
contained text/background overlays are intentional, legible box labels.
