-- Empty legacy table outside M5's built-in JSON migration list.
-- Retain table, column storage and nullability; update only Doctrine type metadata.
ALTER TABLE mautic_intelligent_campaigns_outcomes MODIFY properties LONGTEXT NOT NULL COMMENT '(DC2Type:json)';
