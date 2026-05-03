"""
Keyword-based Tool Finder - An advanced keyword search tool for finding relevant tools.

This tool provides sophisticated keyword matching functionality using natural language
processing techniques including tokenization, stop word removal, stemming, and TF-IDF
scoring for improved relevance ranking. It serves as a robust search method when
AI-powered search methods are unavailable.
"""

import json
import re
import math
from collections import Counter, defaultdict
from typing import Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ToolFinderKeyword")
class ToolFinderKeyword(BaseTool):
    """
    Advanced keyword-based tool finder that uses sophisticated text processing and TF-IDF scoring.

    This class implements natural language processing techniques for tool discovery including:
    - Tokenization and normalization
    - Stop word removal
    - Basic stemming
    - TF-IDF relevance scoring
    - Semantic phrase matching

    The search operates by parsing user queries to extract key terms, processing them through
    NLP pipelines, and matching against pre-built indices of tool metadata for efficient
    and relevant tool discovery.
    """

    # Common English stop words to filter out.
    # NOTE: domain-meaningful terms like "search", "find", "query" are intentionally
    # excluded from this list so that queries like "UniProt search" keep the
    # discriminating token "search" and can match UniProt_search over unrelated tools.
    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "to",
        "was",
        "will",
        "with",
        "the",
        "this",
        "but",
        "they",
        "have",
        "had",
        "what",
        "said",
        "each",
        "which",
        "their",
        "time",
        "up",
        "use",
        "your",
        "how",
        "all",
        "any",
        "can",
        "do",
        "get",
        "if",
        "may",
        "new",
        "now",
        "old",
        "see",
        "two",
        "way",
        "who",
        "boy",
        "did",
        "number",
        "no",
        "long",
        "down",
        "day",
        "came",
        "made",
        "part",
    }

    # Simple stemming rules for common suffixes
    STEMMING_RULES = [
        ("ies", "y"),
        ("ied", "y"),
        ("ying", "y"),
        ("ing", ""),
        ("ly", ""),
        ("ed", ""),
        ("ies", "y"),
        ("ier", "y"),
        ("iest", "y"),
        ("s", ""),
        ("es", ""),
        ("er", ""),
        ("est", ""),
        ("tion", "t"),
        ("sion", "s"),
        ("ness", ""),
        ("ment", ""),
        ("able", ""),
        ("ible", ""),
        ("ful", ""),
        ("less", ""),
        ("ous", ""),
        ("ive", ""),
        ("al", ""),
        ("ic", ""),
        ("ize", ""),
        ("ise", ""),
        ("ate", ""),
        ("fy", ""),
        ("ify", ""),
    ]

    def __init__(self, tool_config, tooluniverse=None):
        """
        Initialize the Advanced Keyword-based Tool Finder.

        Args:
            tool_config (dict): Configuration dictionary for the tool
            tooluniverse: Reference to the ToolUniverse instance containing all tools
        """
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse

        # Extract configuration
        self.name = tool_config.get("name", "ToolFinderKeyword")
        self.description = tool_config.get(
            "description", "Advanced keyword-based tool finder"
        )

        # Tool filtering settings
        self.exclude_tools = tool_config.get(
            "exclude_tools",
            tool_config.get("configs", {}).get(
                "exclude_tools",
                [
                    "Tool_RAG",
                    "Tool_Finder",
                    "Finish",
                    "CallAgent",
                    "ToolFinderLLM",
                    "ToolFinderKeyword",
                ],
            ),
        )
        self.include_categories = tool_config.get("include_categories", None)
        self.exclude_categories = tool_config.get("exclude_categories", None)

        # Initialize tool index for TF-IDF scoring
        self._tool_index = None
        self._document_frequencies = None
        self._total_documents = 0
        self._avg_token_count = (
            0  # average raw token count, used for BM25 normalization
        )

    def _tokenize_and_normalize(self, text: str) -> List[str]:
        """
        Tokenize text and apply normalization including stop word removal and stemming.

        Args:
            text (str): Input text to tokenize

        Returns
            List[str]: List of processed tokens
        """
        if not text:
            return []

        lower_text = text.lower()
        # Extract hyphenated biomedical identifiers (e.g. "il-6" → "il6") before
        # splitting on hyphens, so the compound form is also indexed.
        hyphenated = re.findall(
            r"\b[a-zA-Z][a-zA-Z0-9]*(?:-[a-zA-Z0-9]+)+\b", lower_text
        )
        compound_tokens = [re.sub(r"-", "", h) for h in hyphenated]
        # Extract regular alphanumeric words
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]*\b", lower_text)
        # Add compound forms (e.g. "il6" from "il-6") that aren't already present
        for ct in compound_tokens:
            if ct not in tokens:
                tokens.append(ct)

        # Remove stop words
        tokens = [token for token in tokens if token not in self.STOP_WORDS]

        # Apply basic stemming
        stemmed_tokens = []
        for token in tokens:
            stemmed = self._apply_stemming(token)
            if (
                len(stemmed) >= 2
            ):  # Keep tokens of 2+ chars (allows acronyms like IL, CD)
                stemmed_tokens.append(stemmed)

        return stemmed_tokens

    def _apply_stemming(self, word: str) -> str:
        """
        Apply basic stemming rules to reduce words to their root form.

        Args:
            word (str): Word to stem

        Returns
            str: Stemmed word
        """
        if len(word) <= 3:
            return word

        for suffix, replacement in self.STEMMING_RULES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[: -len(suffix)] + replacement

        return word

    def _extract_phrases(
        self, tokens: List[str], max_phrase_length: int = 3
    ) -> List[str]:
        """
        Extract meaningful phrases from tokens for better semantic matching.

        Args:
            tokens (List[str]): Tokenized words
            max_phrase_length (int): Maximum length of phrases to extract

        Returns
            List[str]: List of phrases and individual tokens
        """
        phrases = []

        # Add individual tokens
        phrases.extend(tokens)

        # Add bigrams and trigrams
        for length in range(2, min(max_phrase_length + 1, len(tokens) + 1)):
            for i in range(len(tokens) - length + 1):
                phrase = " ".join(tokens[i : i + length])
                phrases.append(phrase)

        return phrases

    def _build_tool_index(self, tools: List[Dict]) -> None:
        """
        Build TF-IDF index for all tools to enable efficient relevance scoring.

        Args:
            tools (List[Dict]): List of tool configurations
        """
        self._tool_index = {}
        term_doc_count = defaultdict(int)
        self._total_documents = 0

        for tool in tools:
            tool_name = tool.get("name", "")
            if tool_name in self.exclude_tools:
                continue

            # Combine tool metadata for indexing
            searchable_text = " ".join(
                [
                    tool.get("name", ""),
                    tool.get("description", ""),
                    tool.get("type", ""),
                    tool.get("category", ""),
                    # Include parameter names and descriptions
                    " ".join(self._extract_parameter_text(tool.get("parameter", {}))),
                ]
            )

            # Tokenize and extract phrases
            tokens = self._tokenize_and_normalize(searchable_text)
            phrases = self._extract_phrases(tokens)

            # Build term frequency map for this tool
            term_freq = Counter(phrases)
            self._tool_index[tool_name] = {
                "tool": tool,
                "terms": term_freq,
                "total_terms": len(phrases),
                # raw_token_count stores word-only length for document-length
                # normalization; using phrase count would unfairly penalize tools
                # with longer descriptions that generate more bigrams/trigrams.
                "raw_token_count": len(tokens),
            }

            # Count document frequency for each term
            unique_terms = set(phrases)
            for term in unique_terms:
                term_doc_count[term] += 1

            self._total_documents += 1

        # Calculate document frequencies
        self._document_frequencies = dict(term_doc_count)

        # Compute average raw token count across all indexed documents.
        # Used as the normalization baseline in BM25-style scoring.
        if self._total_documents > 0:
            total_tokens = sum(v["raw_token_count"] for v in self._tool_index.values())
            self._avg_token_count = total_tokens / self._total_documents
        else:
            self._avg_token_count = 1

    def _extract_parameter_text(self, parameter_schema: Dict) -> List[str]:
        """
        Extract searchable text from parameter schema.

        Only parameter **names** are indexed (not their free-text descriptions).
        Parameter descriptions often contain boilerplate phrases like
        "Whether to include usage examples and quick start guide" that
        appear identically across many tools, inflating term frequencies for
        words like "guide" and producing false matches for domain-specific
        queries (e.g. "CRISPR guide RNA design"). Parameter names (e.g.
        "sequence_type", "gene_id", "format") are more discriminating and
        carry genuine signal about tool capabilities.

        Args:
            parameter_schema (Dict): Tool parameter schema

        Returns
            List[str]: List of parameter name text elements
        """
        text_elements = []

        if isinstance(parameter_schema, dict):
            properties = parameter_schema.get("properties", {})
            for prop_name in properties.keys():
                text_elements.append(prop_name)

        return text_elements

    def _calculate_tfidf_score(self, query_terms: List[str], tool_name: str) -> float:
        """
        Calculate BM25-based relevance score for a tool given query terms.

        BM25 (Best Match 25) is a bag-of-words retrieval function that improves
        on plain TF-IDF by incorporating document-length normalization directly
        into the term-frequency saturation formula. This eliminates the bias
        where short tool descriptions (few tokens) score disproportionately
        high because their TF values are inflated by a small denominator.

        BM25 term score for a single term t in document d:
            IDF(t) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))

        where:
            tf    = raw count of term in document
            dl    = document length (raw token count, not phrase count)
            avgdl = average document length across all indexed tools
            k1    = term-frequency saturation parameter (default 1.5)
            b     = document-length normalization strength (default 0.75)

        Using raw_token_count (word-only length, without bigrams/trigrams) as
        dl so that phrase expansion does not double-penalize longer documents.

        Args:
            query_terms (List[str]): Processed query terms and phrases
            tool_name (str): Name of the tool to score

        Returns
            float: BM25 relevance score
        """
        if tool_name not in self._tool_index:
            return 0.0

        tool_data = self._tool_index[tool_name]
        tool_terms = tool_data["terms"]
        total_terms = tool_data["total_terms"]

        # BM25 hyperparameters
        k1 = 1.5  # term-frequency saturation: higher = more weight for repeated terms
        b = 0.75  # document-length normalization strength: 0 = no normalization, 1 = full
        # Discount factor for multi-word phrases: bigrams are worth phrase_discount
        # of a unigram's contribution, trigrams phrase_discount^2, etc. This prevents
        # rare high-IDF n-grams from dominating single-token matches.
        phrase_discount = 0.3

        # Use raw word-only token count as document length (dl).
        # Falls back to total_terms (phrase count) for backward compatibility if
        # the field is absent (index built before this change).
        dl = max(tool_data.get("raw_token_count", total_terms), 1)
        avgdl = max(self._avg_token_count, 1)

        score = 0.0
        query_term_freq = Counter(query_terms)

        for term, query_freq in query_term_freq.items():
            if term in tool_terms:
                tf = tool_terms[term]

                # IDF: log(total docs / docs containing term).
                # Add smoothing (+1) to avoid log(1)=0 for terms in all docs.
                doc_freq = self._document_frequencies.get(term, 1)
                idf = math.log((self._total_documents + 1) / (doc_freq + 0.5))

                # BM25 TF normalization: saturates at high counts and penalizes
                # documents that are longer than average (controlled by b).
                bm25_tf = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))

                # Apply a phrase-length discount so that bigrams and trigrams
                # (which have artificially high IDF due to rarity) do not
                # overwhelm single-token matches. A unigram gets full weight,
                # a bigram gets weight * phrase_discount, a trigram gets
                # weight * phrase_discount^2, etc.
                phrase_length = len(term.split())
                phrase_weight = phrase_discount ** (phrase_length - 1)

                # Optionally weight by query term frequency (log-dampened)
                score += idf * bm25_tf * math.log(1 + query_freq) * phrase_weight

        return score

    def _calculate_exact_match_bonus(self, query: str, tool: Dict) -> float:
        """
        Calculate bonus score for exact matches in tool name or key phrases.

        Tool names use underscores as word separators (e.g. "BLAST_nucleotide_search"),
        so the query is also checked in its underscore-normalized form so that
        "UniProt search" correctly matches "uniprot_search".

        Individual query tokens are also checked against the tool name so that
        a query like "sequence alignment BLAST" gives a bonus to BLAST_nucleotide_search
        even though the full query string does not appear literally in the name.

        Args:
            query (str): Original query string
            tool (Dict): Tool configuration

        Returns
            float: Exact match bonus score
        """
        query_lower = query.lower()
        # Underscore-normalized version of the full query for matching tool names
        query_underscored = query_lower.replace(" ", "_")
        tool_name = tool.get("name", "").lower()
        tool_desc = tool.get("description", "").lower()

        bonus = 0.0

        # Full query (space or underscore form) appears in or equals tool name.
        # Give a larger bonus when the query maps exactly to the tool name
        # (e.g. "UniProt search" → "uniprot_search" == "uniprot_search") versus
        # when the query is merely a prefix of a longer tool name
        # (e.g. "uniprot_search" ⊂ "uniprot_search_uniparc").
        if query_lower == tool_name or query_underscored == tool_name:
            # Exact whole-name match: highest bonus
            bonus += 3.0
        elif (
            query_lower in tool_name
            or tool_name in query_lower
            or query_underscored in tool_name
            or tool_name in query_underscored
        ):
            bonus += 2.0
        else:
            # Partial bonus: count how many individual query tokens appear as
            # exact word-components of the tool name (tool names are
            # underscore-separated, e.g. "BLAST_nucleotide_search" splits into
            # ["blast", "nucleotide", "search"]). Using word-boundary matching
            # prevents "alignment" from matching only because it is a substring
            # of "rfam_get_alignment" — the token must be an entire word in the
            # name. Each matching token adds a small bonus scaled by its length
            # to favour specific acronyms (e.g. "blast") over generic words.
            tool_name_words = set(tool_name.split("_"))
            query_words = query_lower.split()
            token_bonus = 0.0
            for word in query_words:
                if len(word) >= 3 and word in tool_name_words:
                    # Weight by word length: longer/rarer words carry more signal
                    token_bonus += 0.3 * math.log(1 + len(word))
            bonus += token_bonus

        # Exact phrase matches in description
        query_words = query_lower.split()
        if len(query_words) > 1:
            query_phrase = " ".join(query_words)
            if query_phrase in tool_desc:
                bonus += 1.5

        # Category or type exact matches
        tool_type = tool.get("type", "").lower()
        tool_category = tool.get("category", "").lower()

        if query_lower in tool_type or query_lower in tool_category:
            bonus += 1.0

        return bonus

    def find_tools(
        self,
        message=None,
        picked_tool_names=None,
        rag_num=5,
        return_call_result=False,
        categories=None,
    ):
        """
        Find relevant tools based on a message or pre-selected tool names.

        This method matches the interface of other tool finders to ensure
        seamless replacement. It uses keyword-based search instead of embedding similarity.

        Args:
            message (str, optional): Query message to find tools for. Required if picked_tool_names is None.
            picked_tool_names (list, optional): Pre-selected tool names to process. Required if message is None.
            rag_num (int, optional): Number of tools to return after filtering. Defaults to 5.
            return_call_result (bool, optional): If True, returns both prompts and tool names. Defaults to False.
            categories (list, optional): List of tool categories to filter by.

        Returns
            str or tuple:
                - If return_call_result is False: Tool prompts as a formatted string
                - If return_call_result is True: Tuple of (tool_prompts, tool_names)

        Raises:
            AssertionError: If both message and picked_tool_names are None
        """
        if picked_tool_names is None:
            assert picked_tool_names is not None or message is not None

            # Use keyword-based tool search (directly call JSON search to avoid recursion)
            search_result = self._run_json_search(
                {"description": message, "categories": categories, "limit": rag_num}
            )

            # Parse JSON result to extract tool names
            try:
                result_data = json.loads(search_result)
                if result_data.get("error"):
                    picked_tool_names = []
                else:
                    picked_tool_names = [
                        tool["name"] for tool in result_data.get("tools", [])
                    ]
            except json.JSONDecodeError:
                picked_tool_names = []

        # Filter out special tools (matching original behavior)
        picked_tool_names_no_special = []
        for tool in picked_tool_names:
            if tool not in self.exclude_tools:
                picked_tool_names_no_special.append(tool)
        picked_tool_names_no_special = picked_tool_names_no_special[:rag_num]
        picked_tool_names = picked_tool_names_no_special[:rag_num]

        # Get tool objects and prepare prompts (matching original behavior)
        picked_tools = self.tooluniverse.get_tool_specification_by_names(
            picked_tool_names
        )
        picked_tools_prompt = self.tooluniverse.prepare_tool_prompts(picked_tools)

        if return_call_result:
            return picked_tools_prompt, picked_tool_names
        return picked_tools_prompt

    def run(self, arguments):
        """
        Find tools using advanced keyword-based search with NLP processing and TF-IDF scoring.

        This method provides a unified interface compatible with other tool finders.

        Args:
            arguments (dict): Dictionary containing:
                - description (str): Search query string (unified parameter name)
                - categories (list, optional): List of categories to filter by
                - limit (int, optional): Maximum number of results to return (default: 10)
                - picked_tool_names (list, optional): Pre-selected tool names to process
                - return_call_result (bool, optional): Whether to return both prompts and names. Defaults to False.

        Returns
            str or tuple:
                - If return_call_result is False: Tool prompts as a formatted string
                - If return_call_result is True: Tuple of (tool_prompts, tool_names)
        """
        # Extract parameters for compatibility
        description = arguments.get("description", arguments.get("query", ""))
        limit = arguments.get("limit", 10)
        # Default False: find_tools() is the default path (returns a list of tool dicts).
        # Pass True to get (prompts, names) tuple; pass None to use _run_json_search().
        return_call_result = arguments.get("return_call_result", False)
        categories = arguments.get("categories", None)
        picked_tool_names = arguments.get("picked_tool_names", None)

        # If return_call_result is a bool, delegate to find_tools (original interface).
        # If None is explicitly passed, use the JSON search interface.
        if return_call_result is not None:
            return self.find_tools(
                message=description,
                picked_tool_names=picked_tool_names,
                rag_num=limit,
                return_call_result=return_call_result,
                categories=categories,
            )

        # Explicit None: use JSON-based interface (used by CLI directly)
        return self._run_json_search(arguments)

    def _run_json_search(self, arguments):
        """
        Original JSON-based search implementation for backward compatibility.

        Args:
            arguments (dict): Search arguments

        Returns
            str: JSON string containing search results with relevance scores
        """
        try:
            # Extract arguments with unified parameter names
            query = arguments.get(
                "description", arguments.get("query", "")
            )  # Support both names for compatibility
            categories = arguments.get("categories", None)
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0) or 0

            if not query:
                return json.dumps(
                    {
                        "error": "Description parameter is required",
                        "query": query,
                        "tools": [],
                    },
                    indent=2,
                )

            # Feature-R13A-08: queries that look like exact tool names (e.g.
            # "BioGRID_get_chemical_interactions") tokenize to nothing because
            # underscores are treated as separators that produce stop-word-only
            # tokens.  Replacing underscores with spaces lets the NLP pipeline
            # extract the meaningful words ("BioGRID", "chemical", "interactions").
            # Feature-R15B-02: preserve original query for transparency in processing_info.
            query_submitted = query
            if "_" in query:
                query = query.replace("_", " ")

            # Ensure categories is None or a list (handle validation issue)
            if categories is not None and not isinstance(categories, list):
                categories = None

            # Get all tools from tooluniverse
            if not self.tooluniverse:
                return json.dumps(
                    {
                        "error": "ToolUniverse not available",
                        "query": query,
                        "tools": [],
                    },
                    indent=2,
                )

            # AUTO-LOAD: If tools not fully loaded, load them now
            # Check if tools are not loaded or only partially loaded (< 100 tools means incomplete)
            if len(self.tooluniverse.all_tool_dict) < 100:
                self.tooluniverse.logger.info(
                    f"Tool_Finder_Keyword: Only {len(self.tooluniverse.all_tool_dict)} tools loaded, loading all tools now..."
                )
                # Force full load by clearing filters and loading everything
                self.tooluniverse.load_tools(include_tools=None, tool_type=None)

            all_tools = self.tooluniverse.return_all_loaded_tools()

            # Filter by categories if specified
            if categories:
                categories_set = set(categories)
                filtered_tools = [
                    t for t in all_tools if t.get("category") in categories_set
                ]
            else:
                filtered_tools = all_tools

            # Build search index if not already built or if tools changed
            if self._tool_index is None or self._total_documents != len(
                [
                    t
                    for t in filtered_tools
                    if t.get("name", "") not in self.exclude_tools
                ]
            ):
                self._build_tool_index(filtered_tools)

            # Process query using NLP techniques
            query_tokens = self._tokenize_and_normalize(query)
            query_phrases = self._extract_phrases(query_tokens)

            if not query_tokens and not query_phrases:
                # Feature-R13B-01: return standard schema so programmatic consumers
                # can always read total_matches without branching on "error" key.
                return json.dumps(
                    {
                        "query": query,
                        "search_method": "Advanced keyword matching (TF-IDF + NLP)",
                        "total_matches": 0,
                        "limit": limit,
                        "offset": offset,
                        "has_more": False,
                        "categories_filtered": categories,
                        "processing_info": {
                            "query_tokens": 0,
                            "query_phrases": 0,
                            "indexed_tools": getattr(self, "_total_documents", 0),
                            "warning": "No meaningful search terms found in query",
                            **(
                                {
                                    "query_submitted": query_submitted,
                                    "query_normalized": query,
                                }
                                if query_submitted != query
                                else {}
                            ),
                        },
                        "tools": [],
                    },
                    indent=2,
                )

            # Calculate relevance scores for all tools
            tool_scores = []

            for tool in filtered_tools:
                tool_name = tool.get("name", "")

                # Skip excluded tools
                if tool_name in self.exclude_tools:
                    continue

                # Apply category filters if specified
                tool_category = tool.get("category", "unknown")
                if (
                    self.include_categories
                    and tool_category not in self.include_categories
                ):
                    continue
                if self.exclude_categories and tool_category in self.exclude_categories:
                    continue

                # Calculate TF-IDF score
                tfidf_score = self._calculate_tfidf_score(query_phrases, tool_name)

                # Calculate exact match bonus
                exact_bonus = self._calculate_exact_match_bonus(query, tool)

                # Combined relevance score
                total_score = tfidf_score + exact_bonus

                # Only include tools with positive relevance
                if total_score > 0:
                    # tool_name is already shortened (primary identifier)
                    tool_info = {
                        "name": tool_name,
                        "description": tool.get("description", ""),
                        "type": tool.get("type", ""),
                        "category": tool_category,
                        "parameters": tool.get("parameter", {}),
                        # Feature-R12B-03/R13B-04: removed top-level "required" field —
                        # it was always [] (the real list lives inside parameters.required).
                        "relevance_score": round(total_score, 4),
                        "tfidf_score": round(tfidf_score, 4),
                        "exact_match_bonus": round(exact_bonus, 4),
                    }
                    tool_scores.append(tool_info)

            # Sort by relevance score (highest first) and limit results
            tool_scores.sort(key=lambda x: x["relevance_score"], reverse=True)
            total_scored = len(tool_scores)
            matching_tools = tool_scores[offset : offset + limit] if limit > 0 else []

            # Remove internal scoring details from final output
            for tool in matching_tools:
                tool.pop("tfidf_score", None)
                tool.pop("exact_match_bonus", None)

            has_more = (
                total_scored > offset  # limit=0: items exist at this offset
                if limit == 0
                else (
                    limit is not None and (offset + len(matching_tools)) < total_scored
                )
            )
            return json.dumps(
                {
                    "query": query,
                    "search_method": "Advanced keyword matching (TF-IDF + NLP)",
                    "total_matches": total_scored,
                    "limit": limit,
                    "offset": offset,
                    "has_more": has_more,
                    # Feature-R19A-02: include next_offset so pipelines don't recompute
                    # offset + len(tools). Feature-23A-02: when limit=0 and has_more=True,
                    # set next_offset=0 so callers can pass it directly as --offset.
                    "next_offset": (offset + len(matching_tools))
                    if (has_more and limit != 0)
                    else (0 if has_more else None),
                    "categories_filtered": categories,
                    "processing_info": {
                        "query_tokens": len(query_tokens),
                        "query_phrases": len(query_phrases),
                        "indexed_tools": self._total_documents,
                        # Feature-R15B-02: expose original vs normalized query when underscore
                        # normalization was applied, so callers can detect the transformation.
                        **(
                            {
                                "query_submitted": query_submitted,
                                "query_normalized": query,
                            }
                            if query_submitted != query
                            else {}
                        ),
                    },
                    "tools": matching_tools,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {
                    "error": f"Advanced keyword search error: {str(e)}",
                    "query": arguments.get("query", ""),
                    "tools": [],
                },
                indent=2,
            )


# # Tool configuration for ToolUniverse registration
# TOOL_CONFIG = {
#     "name": "ToolFinderKeyword",
#     "description": "Advanced keyword-based tool finder using NLP techniques, TF-IDF scoring, and semantic phrase matching for precise tool discovery",
#     "type": "tool_finder_keyword",
#     "category": "tool_finder",
#     "parameter": {
#         "type": "object",
#         "properties": {
#             "query": {
#                 "type": "string",
#                 "description": "Search query describing the desired functionality. Uses advanced NLP processing including tokenization, stop word removal, and stemming."
#             },
#             "categories": {
#                 "type": "array",
#                 "items": {"type": "string"},
#                 "description": "Optional list of tool categories to filter by"
#             },
#             "limit": {
#                 "type": "integer",
#                 "description": "Maximum number of tools to return, ranked by TF-IDF relevance score (default: 10)",
#                 "default": 10
#             }
#         },
#         "required": ["query"]
#     },
#     "configs": {
#         "exclude_tools": [
#             "Tool_RAG", "Tool_Finder", "Finish", "CallAgent",
#             "ToolFinderLLM", "ToolFinderKeyword"
#         ],
#         "features": [
#             "tokenization", "stop_word_removal", "stemming",
#             "phrase_extraction", "tfidf_scoring", "exact_match_bonus"
#         ]
#     }
# }
