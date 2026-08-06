-- get_inheritors.sql
SELECT nodes.* FROM nodes
JOIN edges ON edges.src = nodes.qualified_name
WHERE edges.dst = ? AND edges.kind = ?
ORDER BY nodes.name;