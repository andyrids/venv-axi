-- get_bases.sql
-- NOTE: Reads `edges` alone - deliberately no JOIN on `nodes`. The
-- walk records an `INHERITS` edge for every base of a walked class,
-- but writes no node row for a base homed in a package it is not
-- walking (`_introspect._walk_class_members`), so a `nodes` JOIN
-- would silently drop exactly the cross-package bases this query
-- exists to report (`specs/commands/inherits.md`, Direction).
-- Ordered by the qualified name - declaration (MRO) order is lost at
-- write time (`specs/commands/inherits.md`, Result ordering).
SELECT dst FROM edges
WHERE src = ? AND kind = ?
ORDER BY dst;
