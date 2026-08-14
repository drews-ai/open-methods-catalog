# Recovery and cleanup provenance

The public implementation derives from Drew Prescott's retained EndWork room-shape
bake-off on the private VM:

```text
/srv/endwork.ai/production/spec-room-rooms-2026-06-03/eval_rooms.py
```

The retained harness compared CareerTech clusters, SOC broad groups, O*NET reported job
titles, and a resolver-shaped view against the same goal: land in the closest work area,
then use the smallest number of facts to reach an exact detailed SOC role.

The private run reported 867 detailed SOC roles, 57,543 title mappings, 46,687 distinct
normalized titles, 6,907 ambiguous titles, and 85.2% unique title resolution at entry.
Those figures are run evidence, not constants in the public implementation.

## Public cleanup

The reference implementation:

- removes absolute VM paths and source-file globbing;
- accepts source-registered aliases and facets from callers;
- removes random sampling and output side effects;
- preserves ambiguous and unsupported states;
- selects only source-backed facets that split every current candidate;
- excludes fuzzy and embedding authority; and
- uses synthetic tests, so no licensed occupation corpus is redistributed.

Any production use must reproduce metrics from a declared source release, publish the
source and transformation manifest, and reconcile the retained 867-role bake-off with
later keystone exports before publication.
