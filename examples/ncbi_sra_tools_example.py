#!/usr/bin/env python3
"""NCBI SRA tools -- sequencing data access examples."""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 80)
    print("NCBI SRA Tools Example")
    print("=" * 80)

    # Example 1: Search for RNA-Seq runs from human samples
    print("\n1. Searching for human RNA-Seq runs...")
    search_result = tu.tools.NCBI_SRA_search_runs(
        operation="search",
        organism="Homo sapiens",
        strategy="RNA-Seq",
        limit=5
    )

    if search_result.get("status") == "success":
        data = search_result.get("data", {})
        print(f"   Found {data.get('count', 0)} total runs")
        print(f"   Returned {data.get('returned', 0)} UIDs")
        print(f"   Search term: {data.get('search_term', '')}")
        uids = data.get("uids", [])
        if uids:
            print(f"   First 3 UIDs: {uids[:3]}")
    else:
        print(f"   Error: {search_result.get('error', 'Unknown error')}")

    # Example 2: Search for SARS-CoV-2 whole genome sequencing
    print("\n2. Searching for SARS-CoV-2 WGS runs...")
    covid_result = tu.tools.NCBI_SRA_search_runs(
        operation="search",
        organism="SARS-CoV-2",
        strategy="WGS",
        platform="ILLUMINA",
        limit=3
    )

    if covid_result.get("status") == "success":
        data = covid_result.get("data", {})
        print(f"   Found {data.get('count', 0)} total runs")
        print(f"   UIDs: {data.get('uids', [])}")
    else:
        print(f"   Error: {covid_result.get('error', 'Unknown error')}")

    # Example 3: Get metadata for specific SRA runs
    print("\n3. Getting metadata for SRA run SRR000001...")
    run_info = tu.tools.NCBI_SRA_get_run_info(
        operation="get_run_info",
        accessions="SRR000001"
    )

    if run_info.get("status") == "success":
        runs = run_info.get("data", [])
        if runs:
            run = runs[0]
            print(f"   Run accession: {run.get('run_accession', 'N/A')}")
            print(f"   Study: {run.get('study_accession', 'N/A')}")
            print(f"   Organism: {run.get('organism', 'N/A')}")
            print(f"   Platform: {run.get('platform', 'N/A')}")
            print(f"   Instrument: {run.get('instrument', 'N/A')}")
            print(f"   Library strategy: {run.get('library_strategy', 'N/A')}")
            print(f"   Library layout: {run.get('library_layout', 'N/A')}")
            print(f"   Total spots: {run.get('total_spots', 'N/A')}")
            print(f"   Total bases: {run.get('total_bases', 'N/A')}")
    else:
        print(f"   Error: {run_info.get('error', 'Unknown error')}")

    # Example 4: Get download URLs
    print("\n4. Getting download URLs for SRR000001 and SRR000002...")
    download_urls = tu.tools.NCBI_SRA_get_download_urls(
        operation="get_download_urls",
        accessions=["SRR000001", "SRR000002"]
    )

    if download_urls.get("status") == "success":
        urls = download_urls.get("data", [])
        for url_info in urls:
            if "error" not in url_info:
                print(f"\n   Accession: {url_info.get('accession', 'N/A')}")
                print(f"   FTP URL: {url_info.get('ftp_url', 'N/A')}")
                print(f"   S3 URL: {url_info.get('s3_url', 'N/A')}")
                print(f"   NCBI URL: {url_info.get('ncbi_url', 'N/A')}")
                print(f"   Note: {url_info.get('note', '')}")
            else:
                print(f"   {url_info.get('accession', 'N/A')}: {url_info.get('error', '')}")
    else:
        print(f"   Error: {download_urls.get('error', 'Unknown error')}")

    # Example 5: Link SRA runs to BioSample
    print("\n5. Linking SRA UID to BioSample...")
    if uids and len(uids) > 0:
        link_result = tu.tools.NCBI_SRA_link_to_biosample(
            operation="link_to_biosample",
            accessions=uids[0]
        )

        if link_result.get("status") == "success":
            links = link_result.get("data", [])
            if links:
                link = links[0]
                print(f"   SRA UID: {link.get('sra_uid', 'N/A')}")
                print(f"   BioSample UIDs: {link.get('biosample_uids', [])}")
                print(f"   BioSample count: {link.get('biosample_count', 0)}")
        else:
            print(f"   Error: {link_result.get('error', 'Unknown error')}")
    else:
        print("   Skipped (no UIDs from search)")

    print("\n" + "=" * 80)
    print("Example completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
