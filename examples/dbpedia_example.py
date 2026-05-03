#!/usr/bin/env python3
"""
DBpedia tools example for ToolUniverse.

This example demonstrates how to use DBpedia SPARQL tool to query
structured knowledge from DBpedia, which is particularly useful for
humanities and social sciences domains.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse


def main():
    """Run DBpedia tools examples."""
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    print("=" * 60)
    print("DBpedia Tools Example")
    print("=" * 60)
    
    # Example 1: Query for people
    print("\n1. Querying DBpedia for people...")
    sparql_query = """
    SELECT ?person ?name ?birthDate WHERE {
        ?person rdf:type dbo:Person .
        ?person rdfs:label ?name .
        ?person dbo:birthDate ?birthDate .
        FILTER(LANG(?name) = 'en')
    } LIMIT 5
    """
    result = tu.run({
        "name": "DBpedia_SPARQL_query",
        "arguments": {
            "sparql": sparql_query,
            "max_results": 5
        }
    })
    print(result)
    
    # Example 2: Query for books
    print("\n2. Querying DBpedia for books...")
    sparql_query = """
    SELECT ?book ?title ?author WHERE {
        ?book rdf:type dbo:Book .
        ?book rdfs:label ?title .
        ?book dbo:author ?author .
        FILTER(LANG(?title) = 'en')
    } LIMIT 5
    """
    result = tu.run({
        "name": "DBpedia_SPARQL_query",
        "arguments": {
            "sparql": sparql_query,
            "max_results": 5
        }
    })
    print(result)
    
    # Example 3: Query for places
    print("\n3. Querying DBpedia for places...")
    sparql_query = """
    SELECT ?place ?name ?country WHERE {
        ?place rdf:type dbo:Place .
        ?place rdfs:label ?name .
        ?place dbo:country ?country .
        FILTER(LANG(?name) = 'en')
    } LIMIT 5
    """
    result = tu.run({
        "name": "DBpedia_SPARQL_query",
        "arguments": {
            "sparql": sparql_query,
            "max_results": 5
        }
    })
    print(result)
    
    # Example 4: Query for specific person information
    print("\n4. Querying DBpedia for information about Shakespeare...")
    sparql_query = """
    SELECT ?property ?value WHERE {
        ?person rdfs:label "William Shakespeare"@en .
        ?person ?property ?value .
        FILTER(LANG(?value) = 'en' || !isLiteral(?value))
    } LIMIT 10
    """
    result = tu.run({
        "name": "DBpedia_SPARQL_query",
        "arguments": {
            "sparql": sparql_query,
            "max_results": 10
        }
    })
    print(result)
    
    # Example 5: Query for historical events
    print("\n5. Querying DBpedia for historical events...")
    sparql_query = """
    SELECT ?event ?name ?date WHERE {
        ?event rdf:type dbo:Event .
        ?event rdfs:label ?name .
        ?event dbo:date ?date .
        FILTER(LANG(?name) = 'en')
    } LIMIT 5
    """
    result = tu.run({
        "name": "DBpedia_SPARQL_query",
        "arguments": {
            "sparql": sparql_query,
            "max_results": 5
        }
    })
    print(result)
    
    # Example 6: Query for organizations
    print("\n6. Querying DBpedia for organizations...")
    sparql_query = """
    SELECT ?org ?name ?founded WHERE {
        ?org rdf:type dbo:Organisation .
        ?org rdfs:label ?name .
        ?org dbo:foundingDate ?founded .
        FILTER(LANG(?name) = 'en')
    } LIMIT 5
    """
    result = tu.run({
        "name": "DBpedia_SPARQL_query",
        "arguments": {
            "sparql": sparql_query,
            "max_results": 5
        }
    })
    print(result)


if __name__ == "__main__":
    main()

