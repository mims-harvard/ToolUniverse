from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Example 1: expression summary for a gene (TP53)
    res1 = tu.run_one_function({
        "name": "GTEx_get_expression_summary",
        "arguments": {"ensembl_gene_id": "ENSG00000141510"}
    })
    print("GTEx_get_expression_summary:", res1 if isinstance(res1, dict) else str(res1)[:500])

    # Example 2: query eQTLs for the gene (small page)
    res2 = tu.run_one_function({
        "name": "GTEx_query_eqtl",
        "arguments": {"ensembl_gene_id": "ENSG00000141510", "page": 1, "size": 5}
    })
    print("GTEx_query_eqtl:", res2 if isinstance(res2, dict) else str(res2)[:500])


if __name__ == "__main__":
    main()
