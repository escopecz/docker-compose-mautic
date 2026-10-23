-- The source lacks the index which M6's charset migration unconditionally drops.
-- Restore the exact index shape from that migration before retrying it.
CREATE INDEX mautic_integration_reference ON mautic_sync_object_mapping (integration(191),integration_object_name(191),integration_reference_id(191),integration_object_id(191));
