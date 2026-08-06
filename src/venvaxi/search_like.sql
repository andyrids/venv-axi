-- search_like.sql
SELECT * FROM nodes
WHERE (name LIKE ? OR qualified_name LIKE ?)
AND (? IS NULL OR package = ?)
ORDER BY
    (lower(name) = lower(?)) DESC,
    (lower(name) LIKE lower(?) || '%') DESC,
    (kind IN ('class', 'function')) DESC,
    length(qualified_name),
    qualified_name
LIMIT ?;
