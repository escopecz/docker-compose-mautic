-- New empty plugin table must match the existing signed emails.id column.
ALTER TABLE mautic_bundle_grapesjsbuilder MODIFY email_id INT DEFAULT NULL;
ALTER TABLE mautic_bundle_grapesjsbuilder ADD CONSTRAINT FK_6158D9A2A832C1C9 FOREIGN KEY (email_id) REFERENCES mautic_emails (id) ON DELETE CASCADE;
