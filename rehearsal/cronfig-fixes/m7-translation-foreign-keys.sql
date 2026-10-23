-- Existing SMS/push IDs are signed INT. Preserve them and match the new links.
ALTER TABLE mautic_sms_messages MODIFY translation_parent_id INT DEFAULT NULL;
ALTER TABLE mautic_sms_messages ADD CONSTRAINT FK_SMS_TRANSLATION_PARENT FOREIGN KEY (translation_parent_id) REFERENCES mautic_sms_messages (id) ON DELETE CASCADE;
ALTER TABLE mautic_push_notifications ADD translation_parent_id INT DEFAULT NULL,
 ADD INDEX IDX_PUSH_NOTIFICATIONS_TRANSLATION_PARENT (translation_parent_id),
 ADD CONSTRAINT FK_PUSH_NOTIFICATIONS_TRANSLATION_PARENT FOREIGN KEY (translation_parent_id) REFERENCES mautic_push_notifications (id) ON DELETE CASCADE;
