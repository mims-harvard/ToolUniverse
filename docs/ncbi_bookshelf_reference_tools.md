# Clinical reference tools: StatPearls, LactMed and LiverTox

Five of these six tools answer from a local index of three open-access NCBI Bookshelf books, built once on the tool host and then kept. The sixth, `EuropePMC_search_case_reports`, is a network search and needs no index.

None of the three books has a search API, and Europe PMC does not index Bookshelf, so the only way to search them is to hold a copy. `tooluniverse.ncbi_bookshelf_index` downloads each archive from [NCBI's literature archive](https://ftp.ncbi.nlm.nih.gov/pub/litarch/), parses it member by member without extracting anything to disk, and writes a compact SQLite index.

## The one-time build

```bash
python -m tooluniverse.ncbi_bookshelf_index build                        # all three
python -m tooluniverse.ncbi_bookshelf_index build --books lactmed livertox
python -m tooluniverse.ncbi_bookshelf_index status
```

| Book | Archive to download | Index kept | Contents |
|---|---|---|---|
| StatPearls (NBK430685) | ~2 GB | ~360 MB | ~8,800 current chapters, section outline, FTS5/BM25 full-text search |
| LactMed (NBK501922) | ~210 MB | ~10 MB | ~1,950 drug records, lactation sections, every listed name |
| LiverTox (NBK547852) | ~200 MB | ~11 MB | ~1,380 drug/class records, hepatotoxicity sections, likelihood score, trade names, master list |

StatPearls is the expensive one; build only the books you need. Archives are deleted after a successful build unless you pass `--keep-archives`. Each index is written under a temporary name and moved into place when complete, so a reader never sees a partial index, and `manifest.json` records each archive's NCBI path, last-updated date and SHA-256 along with record counts and parse failures.

The index directory is `--dir`, else `$TOOLUNIVERSE_BOOKSHELF_DIR`, else `ncbi_bookshelf` under the ToolUniverse user cache directory — normally `~/.cache/tooluniverse/ncbi_bookshelf`. Nothing is written inside the repository, and the indices are not part of the installed package. Point `TOOLUNIVERSE_BOOKSHELF_DIR` at a shared directory to build once and serve several hosts.

Requires SQLite 3.27.0 or newer with FTS5. Until an index exists, each tool returns an error naming the exact build command rather than failing obscurely:

```
The local StatPearls index is not installed
(~/.cache/tooluniverse/ncbi_bookshelf/statpearls.sqlite does not exist).
Build it once with `python -m tooluniverse.ncbi_bookshelf_index build --books statpearls`
(downloads about 2 GB from NCBI and keeps the index), or set
TOOLUNIVERSE_BOOKSHELF_DIR to a directory that holds statpearls.sqlite.
```

Because the five indexed tools are marked `requires_local_input`, they are never called by the repository's own live test tiers; their coverage comes from unit tests against a small fixture index.

## The tools

| Tool | Answers |
|---|---|
| `StatPearls_search` | Full-text search across chapters, ranked by BM25 over title, section heading and section text |
| `StatPearls_get_management` | How a condition is treated: the best-matching chapters' treatment/management sections, optionally with evaluation |
| `StatPearls_get_chapter_section` | One chapter by id (`article-17465`) or title, as its section outline or a named section |
| `LactMed_get_drug` | Breastfeeding safety for one drug: summary of use during lactation, measured milk and infant serum levels, effects, alternatives |
| `LiverTox_get_drug` | Hepatotoxicity for one drug, supplement or class: likelihood score with its wording, background, case reports, mechanism |
| `EuropePMC_search_case_reports` | Published case reports from Europe PMC, with abstracts. Network, no index |

British and American spellings are normalised before searching, so `carcinoid tumour` and `carcinoid tumor` reach the same chapters. For the Europe PMC tool both spellings are searched together, which matters: `TITLE_ABS:(carcinoid tumour)` alone returns 908 case reports and `carcinoid tumor` 3,593, while the combined query returns 4,413.

## Citation and licence

Every result carries its book's citation and licence, and those terms travel with the text:

- **StatPearls** chapters are published under **CC BY-NC-ND 4.0**. They may be redistributed unmodified, with attribution, for non-commercial purposes only. Do not paste chapter text into a commercial product, and do not present an edited version as the chapter.
- **LactMed** (NICHD) and **LiverTox** (NIDDK) are US Government works.
- Europe PMC results are metadata and abstracts under their publishers' terms.

Keep the returned citation with any text you reuse. These are point-of-care reference works written for clinicians, not a substitute for clinical judgement, and a locally built index is only as current as the day it was built — rebuild it to pick up revisions, and check `status` for the last-updated date NCBI recorded.
