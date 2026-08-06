-- schema_fts5.sql
-- External-content FTS5 index over `nodes`, kept in sync via triggers.
CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
    qualified_name, name, doc,
    content='nodes', content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS nodes_fts_insert AFTER INSERT ON nodes BEGIN
    INSERT INTO symbols_fts (rowid, qualified_name, name, doc)
    VALUES (new.rowid, new.qualified_name, new.name, new.doc);
END;

CREATE TRIGGER IF NOT EXISTS nodes_fts_delete AFTER DELETE ON nodes BEGIN
    INSERT INTO symbols_fts (symbols_fts, rowid, qualified_name, name, doc)
    VALUES ('delete', old.rowid, old.qualified_name, old.name, old.doc);
END;

CREATE TRIGGER IF NOT EXISTS nodes_fts_update AFTER UPDATE ON nodes BEGIN
    INSERT INTO symbols_fts (symbols_fts, rowid, qualified_name, name, doc)
    VALUES ('delete', old.rowid, old.qualified_name, old.name, old.doc);
    INSERT INTO symbols_fts (rowid, qualified_name, name, doc)
    VALUES (new.rowid, new.qualified_name, new.name, new.doc);
END;
