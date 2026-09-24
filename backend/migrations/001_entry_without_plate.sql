
ALTER TABLE vehicle_visits ALTER COLUMN plate_number DROP NOT NULL;
ALTER TABLE vehicle_visits ALTER COLUMN entry_time DROP NOT NULL;

ALTER TABLE vehicle_visits ADD COLUMN IF NOT EXISTS vehicle_make text DEFAULT 'unknown';


ALTER TABLE vehicle_visits ADD COLUMN IF NOT EXISTS match_status text DEFAULT 'pending';
