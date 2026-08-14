# Bind instructions and evidence to each event

- Sequence position: 10

Attach source-linked instructions to each work event without turning the graph into an
agent controller. Resolve detail files only inside the declared release root, return
bounded excerpts, and preserve missing or unsafe references as explicit errors.

## Public reference implementation

- [`value_flow.py`](value_flow.py) loads and validates a released value-flow graph,
  returns advisory node views, expands children on demand, resolves confined detail
  references, performs deterministic keyword retrieval, and constructs deviation events
  without writing them.
- [`tests/test_value_flow.py`](tests/test_value_flow.py) covers graph validity, lookup,
  search, bounded detail retrieval, path traversal, cycles, and side-effect-free
  deviation records with synthetic fixtures.
- [`PROVENANCE.md`](PROVENANCE.md) explains what was recovered from Valueflow Forge and
  what changed at the public boundary.

Run:

```bash
python3 -m unittest discover -s tests -v
```

The graph advises. The caller decides whether to follow a node, records authority and
consequence elsewhere, and appends any deviation through the accepted ledger release.
