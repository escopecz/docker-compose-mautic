-- Cronfig rehearsal: four blank header lists fail M5's JSON conversion.
-- Preserve all non-empty values; original M4 checkpoint remains untouched.
UPDATE mautic_emails SET headers='[]' WHERE headers='';
