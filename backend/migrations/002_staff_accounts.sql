-- Staff accounts for the dashboard's login system. One row with is_owner=true
-- is the station owner; everyone else is regular staff. There is no row for
-- a "deleted" former employee -- when someone leaves, the owner repurposes
-- their row (new username/password) for whoever replaces them, rather than
-- the app growing an ever-longer list of accounts nobody can log into.
--
-- updated_at is the session-revocation mechanism: every login token embeds
-- the row's updated_at at the moment it was issued, and every authenticated
-- request re-checks that against the CURRENT row (see backend/auth.py).
-- Changing a username or password bumps updated_at, which invalidates every
-- token issued before that change on its very next use -- the fired
-- employee's existing session stops working immediately, not just after
-- its normal expiry.
--
-- Safe to re-run: CREATE TABLE IF NOT EXISTS is a no-op if it already exists.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS staff_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    display_name text NOT NULL,
    is_owner boolean NOT NULL DEFAULT false,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- No seed row here on purpose: it would need a password hash baked into this
-- file, and pgcrypto's bcrypt output isn't guaranteed to round-trip through
-- every version of the Python bcrypt package the backend uses to verify it.
-- Run create_owner_account.py once after this migration -- it hashes with
-- the exact same library that later verifies logins, so there is no
-- cross-implementation guesswork. See that file for usage.
