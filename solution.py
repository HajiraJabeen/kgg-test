import re
import requests
from datetime import date

# ---------------------------------------------------------------------------
# Pre-resolved Wikidata QIDs for all subjects used in this program.
#
# Reason:-Direct QID lookup (wd:Q37079) is a fast.
# Label-based lookup with skos:altLabel forces a full table scan and 
# times out on Wikidata's public endpoint. Disambiguation is handled in Python, not in SPARQL 
# To extend:  QIDs at https://www.wikidata.org/wiki/Special:Search
# ---------------------------------------------------------------------------
ENTITY_MAP: dict[str, str] = {
    # People
    "Tom Cruise": "Q37079",
    "Madonna":    "Q1744",
    # Cities
    "London":       "Q84",
    "New York":     "Q60",
    "New York City": "Q60",
}


def _age_sparql(qid: str) -> str:
    """
    Fetch date of birth (wdt:P569) for a known entity.
    Age arithmetic is done in Python (_compute_age) so the SPARQL stays
    trivial — no YEAR(NOW()) computation on the server.
    """
    return f"""
    SELECT ?dob WHERE {{
      wd:{qid} wdt:P569 ?dob .
    }}
    LIMIT 1
    """


def _population_sparql(qid: str) -> str:
    """
    Fetch the most recent population figure for a known entity.
    Uses the P1082 (population) statement with its P585 (point in time)
    qualifier to ORDER BY date and take only the latest value.
    """
    return f"""
    SELECT ?pop WHERE {{
      wd:{qid} p:P1082 ?stmt .
      ?stmt ps:P1082 ?pop .
      OPTIONAL {{ ?stmt pq:P585 ?date }}
    }}
    ORDER BY DESC(?date)
    LIMIT 1
    """


def _run_sparql(sparql: str, endpoint: str) -> list[dict]:
    """Execute a SPARQL query against the given endpoint and return bindings."""
    response = requests.get(
        endpoint,
        headers={
            "Accept":     "application/sparql-results+json",
            "User-Agent": "WikidataQuestionAnswerer/1.0",
        },
        params={"query": sparql, "format": "json"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("results", {}).get("bindings", [])


def _parse_intent(question: str) -> tuple[str, str]:
    """
    Extract (intent, subject) from a natural-language question.

    Supported patterns:
      age        — "how old is X", "what age is X", "age of X"
      population — "population of X", "what is the population of X"

    Returns (intent, subject) or raises ValueError.
    """
    q = question.lower().strip().rstrip("?")

    for kw in ["how old is", "what age is", "age of"]:
        if kw in q:
            return "age", q.split(kw)[-1].strip().title()

    m = re.search(r"population of (.+)", q)
    if m:
        return "population", m.group(1).strip().title()

    raise ValueError(f"Unrecognised question pattern: {question!r}")


def _compute_age(dob_str: str) -> int:
    """
    Compute current age from a Wikidata ISO 8601 date string.
    Example input: '1962-07-03T00:00:00Z'
    """
    dob = date.fromisoformat(dob_str[:10])
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


def ask(question: str, endpoint: str = "https://query.wikidata.org/sparql") -> str:
    """
    Answer a natural-language question by querying Wikidata's SPARQL endpoint.

    Supported question types:
      - "How old is <person>?"      → person's current age as a string
      - "What age is <person>?"     → same
      - "What is the population of <place>?" → latest population as a string

    All subjects must have a pre-resolved QID in ENTITY_MAP. This avoids
    expensive label-join queries that time out on Wikidata's public endpoint.

    Args:
        question: Natural language question string.
        endpoint: Wikidata-compatible SPARQL endpoint URL.

    Returns:
        Answer as a plain integer string, e.g. '63' or '8799728'.

    Raises:
        ValueError: If the question pattern or subject is not recognised,
                    or if Wikidata returns no results.
    """
    intent, subject = _parse_intent(question)

    qid = ENTITY_MAP.get(subject)
    if not qid:
        raise ValueError(
            f"No Wikidata QID for {subject!r}. "
            f"Add it to ENTITY_MAP to support this query."
        )

    if intent == "age":
        bindings = _run_sparql(_age_sparql(qid), endpoint)
        if not bindings:
            raise ValueError(f"No date of birth found for {subject!r} ({qid})")
        return str(_compute_age(bindings[0]["dob"]["value"]))

    if intent == "population":
        bindings = _run_sparql(_population_sparql(qid), endpoint)
        if not bindings:
            raise ValueError(f"No population data found for {subject!r} ({qid})")
        return str(int(float(bindings[0]["pop"]["value"])))

    raise ValueError(f"Unhandled intent: {intent!r}")

#point-in-time snapshots will need updating as time progresses
if __name__ == "__main__":
    assert "63" == ask("how old is Tom Cruise")
    assert "67" == ask("what age is Madonna?")
    assert "8799728" == ask("what is the population of London")
    assert "8804190" == ask("what is the population of New York?")
    print("All assertions passed")
