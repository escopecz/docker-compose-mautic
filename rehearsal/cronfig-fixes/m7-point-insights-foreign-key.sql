ALTER TABLE mautic_point_insights MODIFY category_id INT DEFAULT NULL;
ALTER TABLE mautic_point_insights ADD CONSTRAINT FK_9894AA2612469DE2 FOREIGN KEY (category_id) REFERENCES mautic_categories (id) ON DELETE SET NULL;
