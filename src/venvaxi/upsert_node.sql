-- upsert_node.sql
INSERT INTO nodes (
    qualified_name, kind, name, module, signature, doc,
    package, version, home_qualified_name
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (qualified_name) DO UPDATE SET
    kind = excluded.kind,
    name = excluded.name,
    module = excluded.module,
    signature = excluded.signature,
    doc = excluded.doc,
    package = excluded.package,
    version = excluded.version,
    home_qualified_name = excluded.home_qualified_name;