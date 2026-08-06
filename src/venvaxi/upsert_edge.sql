-- upsert_edge.sql
INSERT INTO edges (src, dst, kind)
VALUES (?, ?, ?)
ON CONFLICT (src, dst, kind) DO NOTHING;