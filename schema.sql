CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    password TEXT,
    api_key TEXT,
	admin BOOLEAN DEFAULT false,
    authorized BOOLEAN DEFAULT false,
    joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS sessions (
    token UUID NOT NULL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    expires TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT ((NOW() + interval '1 day') AT TIME ZONE 'UTC'),

    ip INET,
    browser TEXT DEFAULT 'Unknown',
    os TEXT DEFAULT 'UnknownOS'
);

CREATE TABLE IF NOT EXISTS urls (
    owner BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    alias TEXT NOT NULL PRIMARY KEY,
    destination TEXT NOT NULL,
    clicks BIGINT DEFAULT 0 NOT NULL,
    creation_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS notes (
    id UUID NOT NULL PRIMARY KEY DEFAULT (gen_random_uuid()),
    owner BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    content BYTEA NOT NULL,
    has_password BOOLEAN DEFAULT false,
    share_email BOOLEAN DEFAULT True,
    private BOOLEAN DEFAULT false,
    style TEXT DEFAULT 'raw', -- 'raw', 'styled'
    identifier TEXT DEFAULT 'id', -- 'id', 'name'
    clicks BIGINT DEFAULT 0 NOT NULL,
    creation_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    UNIQUE (owner, name)
);

CREATE OR REPLACE FUNCTION deleteOldSessions() RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM sessions CASCADE WHERE expires IS NOT NULL AND expires < now() AT TIME ZONE 'utc';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS oldSessionsExpiry on public.sessions;
CREATE TRIGGER oldSessionsExpiry
    AFTER INSERT OR UPDATE
    ON sessions
    FOR STATEMENT
    EXECUTE PROCEDURE deleteOldSessions();

