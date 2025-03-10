INSERT INTO users (id, google_id, email, name, created_at)
SELECT id, google_id, email, name, created_at
FROM user;