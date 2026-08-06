-- search_fts.sql
SELECT nodes.* FROM symbols_fts
JOIN nodes ON nodes.rowid = symbols_fts.rowid
WHERE symbols_fts MATCH ?
AND (? IS NULL OR nodes.package = ?)
ORDER BY
    (lower(nodes.name) = lower(?)) DESC,
    (lower(nodes.name) LIKE lower(?) || '%') DESC,
    (nodes.kind IN ('class', 'function')) DESC,
    bm25(symbols_fts),
    length(nodes.qualified_name),
    nodes.qualified_name
LIMIT ?;
