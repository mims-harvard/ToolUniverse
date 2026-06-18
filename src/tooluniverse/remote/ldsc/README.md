# LDSC Remote Tool (MCP Server)

Serves [LDSC](https://github.com/CBIIT/ldsc) (LD Score regression; Bulik-Sullivan et al., *Nature Genetics* 2015) — SNP-heritability and genetic correlation from GWAS summary statistics — as ToolUniverse remote tools: `run_ldsc_heritability` and `run_ldsc_genetic_correlation`.

Served remotely (not bundled) because it needs the maintained Python-3 engine
(NCI `CBIIT/ldsc`, the successor to the frozen Python-2.7 `bulik/ldsc`) plus
multi-GB precomputed LD-score reference panels. Hosted alternative for users who
cannot stage the panels: NCI's [LDscore web tool](https://ldlink.nih.gov/ldscore).

## Deploy

```bash
git clone -b ldsc39 https://github.com/CBIIT/ldsc.git /opt/ldsc   # Python-3 engine
pip install -r requirements.txt                                    # numpy scipy pandas bitarray
# Stage LD-score panels (Zenodo): eur_w_ld_chr (record 8182036),
#   S-LDSC baseline set (DOI 10.5281/zenodo.10515792) for partitioned h2.
export LDSC_DIR=/opt/ldsc
export LDSC_REF_DIR=/data/ldsc          # contains eur_w_ld_chr/, w_hm3.snplist, ...
python ldsc_tool.py                      # starts the MCP server on 127.0.0.1:8013
```

Sumstats must be pre-munged (`munge_sumstats.py --merge-alleles w_hm3.snplist`).
Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/ldsc_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
