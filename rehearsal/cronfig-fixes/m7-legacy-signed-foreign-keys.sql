-- Match new foreign-key columns to the unchanged signed legacy parent IDs.
-- Repair both constraints after partial migrations; table/column existence alone
-- is not proof that the original migration finished installing its constraints.
ALTER TABLE mautic_user_invites MODIFY role_id INT NOT NULL;
ALTER TABLE mautic_user_invites ADD CONSTRAINT FK_DFD7C88FD60322AC FOREIGN KEY (role_id) REFERENCES mautic_roles (id) ON DELETE CASCADE;
ALTER TABLE mautic_campaign_events MODIFY redirect_event_id INT DEFAULT NULL;
ALTER TABLE mautic_campaign_events ADD CONSTRAINT FK_86C571AC35451138 FOREIGN KEY (redirect_event_id) REFERENCES mautic_campaign_events (id) ON DELETE SET NULL;
