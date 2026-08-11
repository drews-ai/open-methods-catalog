# Recovered population hierarchy

An improved reference implementation reconstructed from Drew Prescott's
recovered 2025 tessellation corpus.

The historical national run organized 329,260,619 people into:

- 253,385 L0 bindings at an aggregate mean of 1,299.448 people;
- 19,368 L1 territories at an aggregate mean of 17,000.238 people;
- 4,115 L2 parents at an aggregate mean of 80,014.731 people.

The retained counts match a 17,000-person L1 target and the later 80,000-person
L2 rebuild target.

## What the reference core improves

1. Requires a projected CRS before distance calculations.
2. Uses a fixed random seed and child-derived stable IDs.
3. Builds parent geometry from the exact union of assigned children.
4. Conserves population and assigns every child to one parent.
5. Labels household counts as measured or estimated.
6. Blocks publication when population exceptions lack explicit waivers.

## Evidence boundary

The code does not reproduce every byte or phase of the historical Modal build.
It preserves the defensible clustering idea and repairs failures discovered in
the recovered source.

Travel time and farm access remain outside the reference core. The East Texas
prototype labeled straight-line speed estimates as drive time and shifted dense
centers without reading farmable-land data. Add those constraints only with
versioned routing or land inputs, before-and-after assignments, and per-cluster
exception records.

## Run the tests

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

The test suite covers determinism, population conservation, one-parent
membership, exact child-union geometry, projected-CRS enforcement, explicit
waivers, and household-evidence labels.

## Method partials

The Future With AI Method should pin these ranges after GitHub creates a commit:

- `population_hierarchy.py` lines 131–209: build a parent level and record
  population exceptions.
- `population_hierarchy.py` lines 290–325: create stable parents and validate
  child membership, population conservation, and union geometry.

Each range stays under the site's 80-line partial limit.
