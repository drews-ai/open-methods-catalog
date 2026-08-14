PRAGMA foreign_keys = ON;

CREATE TABLE source_registry (
  source_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL,
  title TEXT NOT NULL,
  release TEXT NOT NULL,
  license TEXT NOT NULL,
  locator TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  retrieved_at TEXT NOT NULL
);

CREATE TABLE resolver_release (
  resolver_release_id TEXT PRIMARY KEY,
  taxonomy_release_id TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64),
  status TEXT NOT NULL CHECK (status IN ('draft', 'accepted', 'superseded', 'withdrawn')),
  created_at TEXT NOT NULL,
  accepted_at TEXT
);

CREATE TABLE work_role (
  role_id TEXT PRIMARY KEY,
  soc_code TEXT NOT NULL,
  canonical_title TEXT NOT NULL,
  slug TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  source_release TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'residual', 'deprecated', 'superseded')),
  UNIQUE (soc_code, source_release),
  UNIQUE (slug)
);

CREATE TABLE work_role_alias (
  alias_id TEXT PRIMARY KEY,
  role_id TEXT NOT NULL REFERENCES work_role(role_id),
  raw_label TEXT NOT NULL,
  normalized_label TEXT NOT NULL,
  language TEXT,
  match_kind TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  source_row TEXT NOT NULL,
  UNIQUE (role_id, normalized_label, match_kind, source_id)
);

CREATE INDEX work_role_alias_lookup
  ON work_role_alias (normalized_label, language);

CREATE TABLE browse_node (
  browse_node_id TEXT PRIMARY KEY,
  parent_browse_node_id TEXT REFERENCES browse_node(browse_node_id),
  label TEXT NOT NULL,
  node_kind TEXT NOT NULL CHECK (node_kind IN ('cluster', 'subcluster', 'residual')),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  sort_order INTEGER
);

CREATE TABLE role_browse_edge (
  role_id TEXT NOT NULL REFERENCES work_role(role_id),
  browse_node_id TEXT NOT NULL REFERENCES browse_node(browse_node_id),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  source_path TEXT NOT NULL,
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  PRIMARY KEY (role_id, browse_node_id, source_id)
);

CREATE TABLE role_facet (
  role_id TEXT NOT NULL REFERENCES work_role(role_id),
  axis TEXT NOT NULL,
  value TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  source_path TEXT NOT NULL,
  PRIMARY KEY (role_id, axis, value, source_id)
);

CREATE TABLE labor_surface (
  surface_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  surface_kind TEXT NOT NULL,
  definition TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id)
);

CREATE TABLE role_surface_edge (
  role_id TEXT NOT NULL REFERENCES work_role(role_id),
  surface_id TEXT NOT NULL REFERENCES labor_surface(surface_id),
  relationship TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  observed_at TEXT,
  jurisdiction TEXT,
  confidence TEXT NOT NULL CHECK (confidence IN ('observed', 'supported', 'proposed')),
  PRIMARY KEY (role_id, surface_id, relationship, evidence_locator)
);

CREATE TABLE role_resolution (
  resolution_id TEXT PRIMARY KEY,
  resolver_release_id TEXT NOT NULL REFERENCES resolver_release(resolver_release_id),
  raw_query TEXT NOT NULL,
  normalized_query TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('unsupported', 'ambiguous', 'needs_fact', 'resolved')),
  confirmed_role_id TEXT REFERENCES work_role(role_id),
  confirmation_receipt_id TEXT,
  created_at TEXT NOT NULL,
  CHECK ((status = 'resolved') = (confirmed_role_id IS NOT NULL))
);

CREATE TABLE role_resolution_candidate (
  resolution_id TEXT NOT NULL REFERENCES role_resolution(resolution_id),
  role_id TEXT NOT NULL REFERENCES work_role(role_id),
  candidate_rank INTEGER NOT NULL CHECK (candidate_rank > 0),
  match_kind TEXT NOT NULL,
  matched_label TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  rank_reason TEXT NOT NULL,
  PRIMARY KEY (resolution_id, role_id),
  UNIQUE (resolution_id, candidate_rank)
);
