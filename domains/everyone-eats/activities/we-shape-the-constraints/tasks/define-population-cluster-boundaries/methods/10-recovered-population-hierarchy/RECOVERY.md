# Recovery and provenance

Prepared 2026-08-11 from
`/Users/drewprescott/Downloads/tessellation-pipeline-recovered.zip`.

## Original archive

- ZIP SHA-256: `834df65924fc9c61260749e4313ce3e4dfc3c282d6f0c652cb382ab283251700`
- Primary production file:
  `tessellation-pipeline-v2-run/modal_build_v10_prod.py`
- Production-file SHA-256:
  `150cbae4d32ef9dc34bd5ead25d5ad545c6426ec84f42b3b7c6bb05a9cbc100d`
- 50 preserved revisions of the primary production file.
- 597 declared Windsurf history snapshots plus 13 orphan snapshots.

## Code-to-output match

`run_phases_5_12.py` calculates `int(total_population / 17_000)` and generates
L1 IDs from centroid coordinates and a zero-based index. The surviving output
contains 19,368 L1s and ends with index 19,367 in that same ID format.

`phases_7_8_10.py` uses an 80,000-person L2 target. Floor division of the
retained population yields 4,115, matching the surviving L2 count. The 80,085
target in the production monolith would yield 4,111 and does not explain that
final parent set.

## Historical defects addressed here

- geographic coordinates used as planar distance inputs;
- membership labels and independently drawn Voronoi geometry could disagree;
- validation returned success after warnings;
- household values derived from population lacked an explicit proxy label;
- routed travel and farm-access language exceeded the implemented evidence;
- one Phase 11 branch could reference `scope_list` before assignment.

## Security

The recovered archive remains private. It includes `.env`, historical snapshots,
and credential-shaped assignments. Rotate the affected credentials before
publishing any raw historical excerpt. The files in this folder contain no
recovered secrets.
