-- schema.sql
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS nodes (
    qualified_name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    module TEXT NOT NULL,
    signature TEXT NOT NULL,
    doc TEXT NOT NULL,
    package TEXT NOT NULL,
    version TEXT NOT NULL,
    home_qualified_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (src, dst, kind)
);

-- Records how each package's graph was built, so a shallow walk does
-- not satisfy a later, deeper request (`_cache.is_cache_valid`).
CREATE TABLE IF NOT EXISTS package_builds (
    package TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    max_depth INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_nodes_package ON nodes(package);