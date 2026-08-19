def migrate(cr, version):
    """Rename allowed_range_km -> allowed_range_m and convert values to meters."""
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'attendance_location'
           AND column_name = 'allowed_range_km'
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        ALTER TABLE attendance_location
        RENAME COLUMN allowed_range_km TO allowed_range_m
        """
    )
    cr.execute(
        """
        UPDATE attendance_location
           SET allowed_range_m = allowed_range_m * 1000.0
        """
    )
