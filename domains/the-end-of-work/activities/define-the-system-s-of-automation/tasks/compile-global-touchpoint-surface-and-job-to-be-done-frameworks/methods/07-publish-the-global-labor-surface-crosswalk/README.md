# Publish the global labor-surface crosswalk

- Sequence position: 7

Release stable role identities, source-backed aliases, browse edges, facets, labor
surfaces, resolver runs, unsupported coverage, disagreements, and revision history.

## Public schema specimen

[`role_resolver_schema.sql`](role_resolver_schema.sql) defines the minimum SQLite/D1
tables that keep canonical roles, aliases, browse views, facets, labor surfaces, resolver
releases, candidates, and confirmed resolutions separate.

The schema intentionally does not include agent skills, worker skill claims, automation
scores, or decommission rankings. Those records belong to downstream tasks that reference
`role_id` and `resolver_release_id`.
