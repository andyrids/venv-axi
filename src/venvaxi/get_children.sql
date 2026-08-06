-- get_children.sql
SELECT nodes.* FROM nodes
JOIN edges ON edges.dst = nodes.qualified_name
WHERE edges.src = ? AND edges.kind = ?
ORDER BY nodes.name;