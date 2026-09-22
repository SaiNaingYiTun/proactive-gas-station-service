-- Entry no longer has a plate on this camera setup, and exit-only detections
-- (no matching open visit found) no longer have an entry_time. Both columns
-- must allow NULL. vehicle_make and match_status are new.
--
-- Safe to re-run: DROP NOT NULL is a no-op if already nullable, and the
-- ADD COLUMN IF NOT EXISTS calls are idempotent.

ALTER TABLE vehicle_visits ALTER COLUMN plate_number DROP NOT NULL;
ALTER TABLE vehicle_visits ALTER COLUMN entry_time DROP NOT NULL;

ALTER TABLE vehicle_visits ADD COLUMN IF NOT EXISTS vehicle_make text DEFAULT 'unknown';

-- 'pending'   -- entry recorded, not yet matched to an exit
-- 'matched'   -- exit found exactly one open visit with matching colour/make
-- 'ambiguous' -- exit found more than one candidate; oldest (FIFO) was used
-- 'exit_only' -- exit found no open visit at all; inserted with no entry_time
ALTER TABLE vehicle_visits ADD COLUMN IF NOT EXISTS match_status text DEFAULT 'pending';
