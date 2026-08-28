-- search_fts.sql
SELECT nodes.* FROM symbols_fts
JOIN nodes ON nodes.rowid = symbols_fts.rowid
WHERE symbols_fts MATCH :match
AND (:package IS NULL OR nodes.package = :package)
ORDER BY
    (lower(nodes.name) = lower(:query)) DESC,
    (lower(nodes.name) LIKE lower(:query) || '%') DESC,
    (lower(nodes.qualified_name) = lower(:query)
     OR substr(lower(nodes.qualified_name), -(length(:query) + 1))
        IN ('.' || lower(:query), ':' || lower(:query))) DESC,
    (nodes.kind IN ('class', 'function')) DESC,
    bm25(symbols_fts),
    length(nodes.qualified_name),
    nodes.qualified_name
LIMIT :limit;
