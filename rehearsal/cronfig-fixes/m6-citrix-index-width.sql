-- Preserve all data and the non-unique lookup index while allowing utf8mb4.
-- Full varchar(255) prefixes exceed InnoDB's 3072-byte limit after conversion.
ALTER TABLE mautic_plugin_citrix_events DROP INDEX mautic_citrix_event_product_name,
  ADD INDEX mautic_citrix_event_product_name (product(191),email(191),event_type,event_name(191));
