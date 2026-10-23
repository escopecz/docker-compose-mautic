-- M7's typed array cannot hydrate the legacy serialized-null preference value.
-- Empty preferences remain empty; preserve all populated preference arrays.
UPDATE mautic_users SET preferences='a:0:{}' WHERE preferences='N;' OR preferences IS NULL;
