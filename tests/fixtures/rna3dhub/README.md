Responses recorded from https://rna.bgsu.edu/rna3dhub on 2026-11-25
(representative-set release 4.66, Motif Atlas release 4.16). No key.

- `nrlist_current_1.5A.csv`: `/nrlist/download/current/1.5A/csv`, complete
  (164 classes). The server sends the rows in a new order on every request.
- `nrlist_current_all.csv`: 3 of the 5,281 rows of
  `/nrlist/download/current/all/csv`: the classes of 7DOL, 4TNA and 7TZS.
- `nrlist_invalid_release.txt`: `/nrlist/download/9.99/1.5A/csv`. HTTP 200.
- `motifs_hl_current.json`: 6 of the 256 groups of
  `/motifs/release/hl/current/json`, each group complete.
- `motif_IL_03350.3.json`: `/motif/view/IL_03350.3/json`, complete.
- `motif_404.json`: `/motif/view/HL_99999.9/json`. HTTP 404.
- `motifs_release_404.json`: `/motifs/release/hl/9.99/json`. HTTP 404.
- `loops_4TNA.csv`: `/loops/download/4TNA`, complete (yeast tRNA-Phe).
- `loops_none.txt`: `/loops/download/7DOL`. HTTP 200. 7DOL is an RNA entry
  with no loop. The server sends the same body for an id that does not exist.
