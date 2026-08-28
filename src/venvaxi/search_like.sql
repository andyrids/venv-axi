-- search_like.sql
SELECT * FROM nodes
WHERE (
    name LIKE :pattern
    OR qualified_name LIKE :pattern
    -- `:doc_pattern` is NULL for a path-shaped query: a docstring that
    -- mentions a symbol is prose about it, not a spelling of it.
    OR (:doc_pattern IS NOT NULL AND doc LIKE :doc_pattern)
)
AND (:package IS NULL OR package = :package)
ORDER BY
    (lower(name) = lower(:query)) DESC,
    (lower(name) LIKE lower(:query) || '%') DESC,
    (lower(qualified_name) = lower(:query)
     OR substr(lower(qualified_name), -(length(:query) + 1))
        IN ('.' || lower(:query), ':' || lower(:query))) DESC,
    (kind IN ('class', 'function')) DESC,
    length(qualified_name),
    qualified_name
LIMIT :limit;
