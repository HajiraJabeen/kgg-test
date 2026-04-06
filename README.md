# KGG Technical Test — `ask()`

Natural language question answering over Wikidata's public SPARQL endpoint.

## Approach

The `ask()` function parses a natural language question into an **intent** (`age` or `population`) and a **subject** (`Tom Cruise`, `London`, etc.), resolves the subject to a Wikidata QID via a local lookup table, and runs a minimal SPARQL query against the Wikidata endpoint.

**Using a lookup table**  
Wikidata's public endpoint times out on open-ended label joins (e.g. via `skos:altLabel`). Direct QID lookups (`wd:Q37079`) hit the primary index and respond in under a second. Disambiguation is a Python concern, not a SPARQL one.

**Computing age in Python**  
Keeping the SPARQL trivial (just fetch the DOB) makes it faster and easier to test. Age arithmetic in Python is also more readable and handles edge cases (birthday not yet passed this year) clearly.

## Setup

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd kgg-test

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the solution
python solution.py
```

Expected output:
```
All assertions passed
```

## Extending

To support new subjects, add their Wikidata QID to `ENTITY_MAP` in `solution.py`:

```python
ENTITY_MAP = {
    "Elon Musk": "Q317521",   # person → age query
    "Paris":     "Q90",       # city  → population query
    ...
}
```

Find QIDs at [wikidata.org/wiki/Special:Search](https://www.wikidata.org/wiki/Special:Search).

## Dependencies

| Package    | Purpose                        |
|------------|--------------------------------|
| `requests` | HTTP calls to the SPARQL endpoint |

No API keys required. The solution queries Wikidata's freely available public endpoint.
