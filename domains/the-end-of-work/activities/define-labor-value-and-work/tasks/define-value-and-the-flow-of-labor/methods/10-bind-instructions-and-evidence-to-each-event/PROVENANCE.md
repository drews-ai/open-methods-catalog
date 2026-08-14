# Recovery provenance

## Recovered implementation

The private EndWork VM retains an owner-authored Valueflow Forge under
`/srv/valueflow-forge`. Its Phase 1 SEO release contains a source-derived work graph and
a six-operation resolver. The recovered resolver established the useful product rule:
the graph supplies prior structure and evidence, while the agent's own loop decides what
to do.

Private source used for comparison:

- `/srv/valueflow-forge/resolver/core.py`
- `/srv/valueflow-forge/scripts/validate_flow.py`
- `/srv/valueflow-forge/resolver/smoke_test.py`
- `/srv/valueflow-forge/output/seo.flow.json`

The private corpus, run logs, generated SEO graph, and practitioner detail files are not
copied here.

## Public cleanup

The public implementation preserves advisory lookup, expansion, detail retrieval,
keyword search, and deviation construction. It changes the boundary deliberately:

- validates graph identity, parentage, child references, and cycles before lookup;
- confines every detail reference to a declared release root after symlink resolution;
- bounds returned detail bytes;
- requires the caller to supply the event timestamp;
- returns a deviation record instead of writing to a shared file; and
- uses synthetic tests rather than private practitioner material.

The recovered resolver joined paths without proving confinement and appended deviations
directly. Those behaviors are recovery evidence, not the recommended public contract.

## Claim boundary

This specimen proves deterministic graph validation and retrieval behavior. It does not
prove the correctness or completeness of the private SEO release, permission to
redistribute its source corpus, practitioner acceptance, generalization to another work
domain, or authority to execute any described work.
