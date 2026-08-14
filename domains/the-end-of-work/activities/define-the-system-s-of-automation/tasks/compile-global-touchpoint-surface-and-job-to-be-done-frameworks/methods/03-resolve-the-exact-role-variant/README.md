# Resolve the exact role variant

- Sequence position: 3

Resolve a title through source-backed aliases. Return an exact canonical role when the
mapping is unique. When several roles remain, select the declared facet that reduces the
candidate set most and ask only that question. Preserve ambiguity when no source-backed
fact can finish the resolution.

## Public reference implementation

- [`role_resolver.py`](role_resolver.py) implements deterministic normalization, exact
  alias resolution, adaptive facet selection, explicit unresolved states, and structural
  evaluation metrics.
- [`tests/test_role_resolver.py`](tests/test_role_resolver.py) proves unique, ambiguous,
  unsupported, and facet-resolved paths with synthetic records.
- [`PROVENANCE.md`](PROVENANCE.md) describes the recovered VM harness and the boundary
  between retained results and the cleaned public implementation.

The implementation deliberately excludes fuzzy and embedding matches. Those systems may
suggest candidates, but they cannot establish a role identity without confirmation.

## Run

```bash
python3 -m unittest discover -s tests -v
```

No occupational source data is committed here. Callers load their own licensed,
source-registered aliases and facets.
