-- Original recordings are private. Access will be granted through user-specific
-- Storage policies when authentication is added.
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('recordings', 'recordings', false, 524288000)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = EXCLUDED.file_size_limit;
