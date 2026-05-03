# Advanced Tool Implementation Patterns

This reference covers advanced patterns and techniques for ToolUniverse tool development.

## Offline / Computational Tools

Some tools require no network access at all — they perform purely local calculations using
mathematical formulas, lookup tables, or parametric models.  These tools are faster, more
reliable, and easier to test than API-backed tools.

### Minimal Offline Tool Skeleton

```python
# my_calculator_tool.py
import math
from typing import Dict, Any, Optional
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

@register_tool("MyCalculatorTool")
class MyCalculatorTool(BaseTool):
    """
    Brief description.  Runs entirely offline — no network requests.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "default_op")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # operation can come from fields (set in JSON) or runtime arg
            op = arguments.get("operation") or self.operation

            def _get(key: str) -> Optional[float]:
                val = arguments.get(key)
                return float(val) if val is not None else None

            x = _get("x")
            if x is None:
                return {"status": "error", "message": "Missing required parameter: x"}

            result_value = x * 2          # your formula here

            return {
                "status": "success",
                "data": {
                    "operation": op,
                    "result": result_value,
                    "result_formatted": f"{result_value:.4g}",
                },
                "metadata": {
                    "note": "Runs offline — no network request.",
                    "formula": "result = x × 2",
                },
            }
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}
```

Key rules for offline tools:
- Return `{"status": "error", "message": "..."}` — use `"message"` (not `"error"`) to match the circuit plugin convention.
- Include a `"metadata"` block that names the formula(s) used and notes "Runs offline".
- Always `float(val)` when extracting numeric arguments from the dict (they may arrive as strings).
- Use `ValueError` for domain validation; let the outer `except Exception` catch everything else.

### SI Formatting Helper

Include a local `_fmt_si()` helper in every offline calculation tool for consistent output:

```python
def _fmt_si(value: float, unit: str) -> str:
    """Format a numeric value with SI prefix and unit label."""
    abs_v = abs(value)
    if abs_v == 0:
        return f"0 {unit}"
    if abs_v >= 1e9:  return f"{value / 1e9:.4g} G{unit}"
    if abs_v >= 1e6:  return f"{value / 1e6:.4g} M{unit}"
    if abs_v >= 1e3:  return f"{value / 1e3:.4g} k{unit}"
    if abs_v >= 1:    return f"{value:.4g} {unit}"
    if abs_v >= 1e-3: return f"{value * 1e3:.4g} m{unit}"
    if abs_v >= 1e-6: return f"{value * 1e6:.4g} µ{unit}"
    if abs_v >= 1e-9: return f"{value * 1e9:.4g} n{unit}"
    return f"{value * 1e12:.4g} p{unit}"
```

Always include both the raw numeric field and a `_formatted` string sibling so LLMs can
display human-readable values without reformatting:

```python
"data": {
    "delay_ps": 34.0,
    "delay_formatted": "34 ps",        # human-readable sibling
    "frequency_Hz": 4.66e9,
    "frequency_formatted": "4.66 GHz", # human-readable sibling
}
```

### Technology-Node Lookup Tables

Many chip-design quantities are tabulated per process node.  Use a `Dict[int, ...]` keyed
by node in nm with a `_nearest_node()` helper that falls back to the closest entry:

```python
# Empirical FO4 delay values in ps, one per node
_FO4_TABLE: Dict[int, float] = {
    180: 250.0,
    130: 170.0,
    90:  115.0,
    65:   80.0,
    45:   55.0,
    32:   40.0,
    28:   34.0,
    20:   26.0,
    16:   20.0,
    10:   15.0,
    7:    11.0,
}

_SORTED_NODES = sorted(_FO4_TABLE.keys())

def _nearest_node(node_nm: float) -> int:
    """Return the nearest supported technology node for a given nm value."""
    return min(_SORTED_NODES, key=lambda n: abs(n - node_nm))
```

When the user's requested node is not in the table, include a `"warning"` field (not an
error) in the data dict and continue with the nearest match:

```python
nearest = _nearest_node(node_nm)
fo4_ps  = _FO4_TABLE[nearest]

warning = None
if nearest != int(node_nm):
    warning = (
        f"Node {node_nm} nm not in table; "
        f"using nearest supported node {nearest} nm."
    )

result = {
    "node_nm": nearest,
    "fo4_delay_ps": fo4_ps,
    # ...
}
if warning:
    result["warning"] = warning      # add only when needed
```

Also expose `"supported_nodes_nm": _SORTED_NODES` in the response so callers know which
values are available without reading the source code.

### Warning Fields vs Error Returns

Use these two patterns consistently:

| Situation | Pattern |
|---|---|
| Input is technically valid but uses a fallback (e.g. nearest node) | `data["warning"] = "..."` — return `status: success` |
| Input violates a hard physical constraint (e.g. negative capacitance) | `raise ValueError("...")` — caught → `status: error, message: ...` |
| A computed threshold is exceeded (e.g. ground bounce > 100 mV) | `data["warning"] = "..."` + `data["exceeds_threshold"] = True` — still `status: success` |

Example — threshold warning pattern:

```python
THRESHOLD_V = 0.100  # 100 mV

v_noise = L * n * di_dt   # computation
exceeds = v_noise > THRESHOLD_V

result = {
    "ground_bounce_V":    v_noise,
    "ground_bounce_mV":   v_noise * 1e3,
    "exceeds_threshold":  exceeds,
}
if exceeds:
    result["warning"] = (
        f"Ground bounce {v_noise * 1e3:.1f} mV exceeds "
        f"{THRESHOLD_V * 1e3:.0f} mV threshold."
    )
```

### Multi-Operation Offline Tool (fields.operation dispatch)

For tools that share the same physics domain but have multiple distinct computations,
use the `fields.operation` dispatch pattern.  The JSON config stores the default operation
in `"fields": { "operation": "op_name" }`, and the runtime argument can override it:

```python
# In JSON config (one entry per operation):
{
  "name": "Circuit_fo4_delay",
  "type": "FO4DelayTool",
  "fields": { "operation": "lookup" },    # default for this tool entry
  ...
}

# In __init__:
def __init__(self, tool_config):
    super().__init__(tool_config)
    self.operation = tool_config.get("fields", {}).get("operation", "lookup")

# In run():
op = arguments.get("operation") or self.operation   # runtime arg takes priority
if op == "lookup":
    ...
elif op == "estimate_path":
    ...
else:
    return {"status": "error", "message": f"Unknown operation '{op}'.  Valid: ..."}
```

This lets you expose a single Python class and multiple JSON entries (one per default
operation) — or a single JSON entry that accepts the operation as a runtime argument.

## Caching Strategies

### Simple LRU Cache

```python
from functools import lru_cache
import json

@register_tool("CachedAPITool")
class CachedAPITool(BaseTool):
    """Tool with response caching."""
    
    @lru_cache(maxsize=128)
    def _cached_request(self, url: str, params_json: str):
        """Cache API responses using LRU cache."""
        params = json.loads(params_json)
        response = requests.get(url, params=params)
        return response.json()
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = "https://api.example.com/data"
        
        # Convert params to JSON string for cache key
        params_json = json.dumps(arguments, sort_keys=True)
        
        try:
            data = self._cached_request(url, params_json)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

### Time-Based Cache

```python
from datetime import datetime, timedelta
from typing import Optional

@register_tool("TimeCachedTool")
class TimeCachedTool(BaseTool):
    """Tool with time-based caching."""
    
    def __init__(self):
        super().__init__()
        self._cache = {}
        self._cache_timeout = timedelta(minutes=15)
    
    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached value if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_timeout:
                return data
            else:
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, data: Dict):
        """Store value in cache with timestamp."""
        self._cache[key] = (data, datetime.now())
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cache_key = json.dumps(arguments, sort_keys=True)
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            return {
                "status": "success",
                "data": cached,
                "cached": True
            }
        
        # Fetch fresh data
        try:
            response = requests.get(url, params=arguments)
            data = response.json()
            
            # Store in cache
            self._set_cached(cache_key, data)
            
            return {
                "status": "success",
                "data": data,
                "cached": False
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

## Batch Processing

### Batch Request Tool

```python
from typing import List

@register_tool("BatchTool")
class BatchTool(BaseTool):
    """Process multiple requests in a single call."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ids = arguments.get('ids', [])
        batch_size = arguments.get('batch_size', 10)
        
        if not ids:
            return {
                "status": "error",
                "error": "ids parameter is required"
            }
        
        results = []
        errors = []
        
        # Process in batches
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            
            try:
                batch_results = self._fetch_batch(batch)
                results.extend(batch_results)
            except Exception as e:
                errors.append({
                    "batch": batch,
                    "error": str(e)
                })
        
        return {
            "status": "success" if not errors else "partial",
            "count": len(results),
            "results": results,
            "errors": errors if errors else None
        }
    
    def _fetch_batch(self, ids: List[str]) -> List[Dict]:
        """Fetch data for a batch of IDs."""
        response = requests.post(
            "https://api.example.com/batch",
            json={"ids": ids},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
```

### Parallel Requests

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

@register_tool("ParallelTool")
class ParallelTool(BaseTool):
    """Execute multiple requests in parallel."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ids = arguments.get('ids', [])
        max_workers = min(arguments.get('max_workers', 5), 10)
        
        results = []
        errors = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all requests
            future_to_id = {
                executor.submit(self._fetch_single, id_): id_
                for id_ in ids
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_id):
                id_ = future_to_id[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append({
                        "id": id_,
                        "error": str(e)
                    })
        
        return {
            "status": "success" if not errors else "partial",
            "count": len(results),
            "results": results,
            "errors": errors if errors else None
        }
    
    def _fetch_single(self, id_: str) -> Dict:
        """Fetch data for a single ID."""
        response = requests.get(
            f"https://api.example.com/items/{id_}",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
```

## Streaming and Pagination

### Auto-Pagination Tool

```python
@register_tool("AutoPaginationTool")
class AutoPaginationTool(BaseTool):
    """Automatically fetch all pages."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query')
        max_pages = arguments.get('max_pages', 10)
        
        all_results = []
        page = 1
        
        while page <= max_pages:
            try:
                response = requests.get(
                    "https://api.example.com/search",
                    params={
                        'query': query,
                        'page': page,
                        'page_size': 100
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                all_results.extend(results)
                
                # Stop if no more results
                if not data.get('next'):
                    break
                
                page += 1
                
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed on page {page}: {str(e)}",
                    "partial_results": all_results
                }
        
        return {
            "status": "success",
            "count": len(all_results),
            "pages": page,
            "results": all_results
        }
```

### Cursor-Based Pagination

```python
@register_tool("CursorPaginationTool")
class CursorPaginationTool(BaseTool):
    """Handle cursor-based pagination."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        cursor = arguments.get('cursor')
        page_size = arguments.get('page_size', 20)
        
        params = {'page_size': page_size}
        if cursor:
            params['cursor'] = cursor
        
        try:
            response = requests.get(
                "https://api.example.com/items",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": "success",
                "count": len(data.get('results', [])),
                "next_cursor": data.get('next_cursor'),
                "has_more": data.get('has_more', False),
                "results": data.get('results', [])
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

## Authentication Patterns

### API Key Authentication

```python
import os

@register_tool("APIKeyTool")
class APIKeyTool(BaseTool):
    """Tool with API key authentication."""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get('API_KEY')
        if not self.api_key:
            raise ValueError("API_KEY environment variable not set")
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.get(
                "https://api.example.com/data",
                headers={"X-API-Key": self.api_key},
                params=arguments,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

### OAuth Token Authentication

```python
@register_tool("OAuthTool")
class OAuthTool(BaseTool):
    """Tool with OAuth token authentication."""
    
    def __init__(self):
        super().__init__()
        self.token = self._get_token()
    
    def _get_token(self) -> str:
        """Get or refresh OAuth token."""
        client_id = os.environ.get('CLIENT_ID')
        client_secret = os.environ.get('CLIENT_SECRET')
        
        response = requests.post(
            "https://api.example.com/oauth/token",
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
        )
        response.raise_for_status()
        return response.json()['access_token']
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.get(
                "https://api.example.com/data",
                headers={"Authorization": f"Bearer {self.token}"},
                params=arguments,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json()
            }
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                # Token expired, refresh and retry
                self.token = self._get_token()
                return self.run(arguments)
            return {
                "status": "error",
                "error": str(e)
            }
```

## Data Transformation

### Field Selection and Projection

```python
@register_tool("ProjectionTool")
class ProjectionTool(BaseTool):
    """Tool with field selection support."""
    
    ALLOWED_FIELDS = {
        'id', 'name', 'description', 'created_date',
        'updated_date', 'status', 'author', 'tags'
    }
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        id_ = arguments.get('id')
        fields = arguments.get('fields', ['id', 'name'])
        
        # Validate fields
        invalid = set(fields) - self.ALLOWED_FIELDS
        if invalid:
            return {
                "status": "error",
                "error": f"Invalid fields: {invalid}",
                "allowed_fields": list(self.ALLOWED_FIELDS)
            }
        
        try:
            # Fetch full data
            response = requests.get(
                f"https://api.example.com/items/{id_}",
                timeout=30
            )
            response.raise_for_status()
            full_data = response.json()
            
            # Project only requested fields
            projected = {
                k: v for k, v in full_data.items()
                if k in fields
            }
            
            return {
                "status": "success",
                "data": projected
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

### Data Filtering

```python
@register_tool("FilterTool")
class FilterTool(BaseTool):
    """Tool with client-side filtering."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query')
        filters = arguments.get('filters', {})
        
        try:
            # Fetch data
            response = requests.get(
                "https://api.example.com/search",
                params={'query': query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Apply filters
            results = data.get('results', [])
            filtered = self._apply_filters(results, filters)
            
            return {
                "status": "success",
                "count": len(filtered),
                "total": len(results),
                "results": filtered
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filters to results."""
        filtered = results
        
        # Status filter
        if 'status' in filters:
            status = filters['status']
            filtered = [r for r in filtered if r.get('status') == status]
        
        # Date range filter
        if 'date_from' in filters:
            date_from = filters['date_from']
            filtered = [
                r for r in filtered
                if r.get('date', '') >= date_from
            ]
        
        if 'date_to' in filters:
            date_to = filters['date_to']
            filtered = [
                r for r in filtered
                if r.get('date', '') <= date_to
            ]
        
        # Tag filter
        if 'tags' in filters:
            required_tags = set(filters['tags'])
            filtered = [
                r for r in filtered
                if required_tags.issubset(set(r.get('tags', [])))
            ]
        
        return filtered
```

## GraphQL Integration

### GraphQL Query Tool

```python
@register_tool("GraphQLTool")
class GraphQLTool(BaseTool):
    """Execute GraphQL queries."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query')
        variables = arguments.get('variables', {})
        
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required"
            }
        
        try:
            response = requests.post(
                "https://api.example.com/graphql",
                json={
                    'query': query,
                    'variables': variables
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL errors
            if 'errors' in result:
                return {
                    "status": "error",
                    "error": "GraphQL query failed",
                    "details": result['errors']
                }
            
            return {
                "status": "success",
                "data": result.get('data')
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

### GraphQL with Predefined Queries

```python
@register_tool("PredefinedGraphQLTool")
class PredefinedGraphQLTool(BaseTool):
    """GraphQL tool with predefined queries."""
    
    QUERIES = {
        'get_drug': """
            query GetDrug($id: ID!) {
                drug(id: $id) {
                    id
                    name
                    description
                    manufacturer
                }
            }
        """,
        'search_drugs': """
            query SearchDrugs($query: String!, $limit: Int) {
                searchDrugs(query: $query, limit: $limit) {
                    id
                    name
                    manufacturer
                }
            }
        """
    }
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get('operation')
        variables = arguments.get('variables', {})
        
        if operation not in self.QUERIES:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(self.QUERIES.keys())
            }
        
        query = self.QUERIES[operation]
        
        try:
            response = requests.post(
                "https://api.example.com/graphql",
                json={
                    'query': query,
                    'variables': variables
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if 'errors' in result:
                return {
                    "status": "error",
                    "error": "GraphQL query failed",
                    "details": result['errors']
                }
            
            return {
                "status": "success",
                "data": result.get('data')
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

## Rate Limiting

### Simple Rate Limiter

```python
from time import time, sleep
from collections import deque

@register_tool("RateLimitedTool")
class RateLimitedTool(BaseTool):
    """Tool with rate limiting."""
    
    def __init__(self):
        super().__init__()
        self.requests = deque()
        self.max_requests = 10  # 10 requests
        self.time_window = 60   # per 60 seconds
    
    def _wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time()
        
        # Remove requests outside time window
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # Wait if at limit
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                sleep(sleep_time)
            self.requests.popleft()
        
        # Record this request
        self.requests.append(now)
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self._wait_if_needed()
        
        try:
            response = requests.get(
                "https://api.example.com/data",
                params=arguments,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "status": "success",
                "data": response.json()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

## Webhook and Async Operations

### Async Job Polling Tool

```python
@register_tool("AsyncJobTool")
class AsyncJobTool(BaseTool):
    """Tool that polls for async job completion."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query')
        timeout = arguments.get('timeout', 300)  # 5 minutes default
        poll_interval = arguments.get('poll_interval', 5)  # 5 seconds
        
        try:
            # Start async job
            response = requests.post(
                "https://api.example.com/jobs",
                json={'query': query},
                timeout=30
            )
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data['job_id']
            
            # Poll for completion
            start_time = time()
            while time() - start_time < timeout:
                status_response = requests.get(
                    f"https://api.example.com/jobs/{job_id}",
                    timeout=30
                )
                status_response.raise_for_status()
                status = status_response.json()
                
                if status['state'] == 'completed':
                    return {
                        "status": "success",
                        "job_id": job_id,
                        "data": status['result']
                    }
                elif status['state'] == 'failed':
                    return {
                        "status": "error",
                        "error": "Job failed",
                        "detail": status.get('error')
                    }
                
                sleep(poll_interval)
            
            return {
                "status": "timeout",
                "error": f"Job did not complete within {timeout} seconds",
                "job_id": job_id
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

## Multi-Source Aggregation

### Aggregation Tool

```python
@register_tool("AggregationTool")
class AggregationTool(BaseTool):
    """Aggregate data from multiple sources."""
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query')
        sources = arguments.get('sources', ['source1', 'source2', 'source3'])
        
        results = []
        errors = []
        
        for source in sources:
            try:
                data = self._fetch_from_source(source, query)
                results.extend(data)
            except Exception as e:
                errors.append({
                    "source": source,
                    "error": str(e)
                })
        
        # Deduplicate by ID
        seen_ids = set()
        unique_results = []
        for result in results:
            id_ = result.get('id')
            if id_ not in seen_ids:
                seen_ids.add(id_)
                unique_results.append(result)
        
        return {
            "status": "success" if not errors else "partial",
            "count": len(unique_results),
            "sources_queried": len(sources),
            "sources_failed": len(errors),
            "results": unique_results,
            "errors": errors if errors else None
        }
    
    def _fetch_from_source(self, source: str, query: str) -> List[Dict]:
        """Fetch data from a specific source."""
        url_map = {
            'source1': 'https://api1.example.com/search',
            'source2': 'https://api2.example.com/query',
            'source3': 'https://api3.example.com/find'
        }
        
        url = url_map.get(source)
        if not url:
            raise ValueError(f"Unknown source: {source}")
        
        response = requests.get(url, params={'q': query}, timeout=30)
        response.raise_for_status()
        
        return response.json().get('results', [])
```
