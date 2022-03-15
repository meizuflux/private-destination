CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT,
    avatar_url TEXT,
    api_key TEXT,
    oauth_provider TEXT NOT NULL,
	admin BOOLEAN DEFAULT false,
    joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS sessions (
    token UUID NOT NULL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    expires TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT ((NOW() + interval '1 day') AT TIME ZONE 'UTC'),

    browser TEXT DEFAULT 'Unknown',
    os TEXT DEFAULT 'UnknownOS'
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

CREATE TABLE IF NOT EXISTS urls (
    owner BIGINT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    key TEXT NOT NULL PRIMARY KEY,
    destination TEXT NOT NULL,
    clicks BIGINT DEFAULT 0 NOT NULL,
    creation_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);