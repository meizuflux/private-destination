CREATE TABLE IF NOT EXISTS notes (
    id UUID NOT NULL PRIMARY KEY DEFAULT (gen_random_uuid()),
    owner BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    content BYTEA NOT NULL,
    has_password BOOLEAN DEFAULT false,
    share_email BOOLEAN DEFAULT True,
    private BOOLEAN DEFAULT false,
    clicks BIGINT DEFAULT 0 NOT NULL,
    creation_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);
