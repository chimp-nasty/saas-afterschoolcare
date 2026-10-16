INSERT INTO auth.roles (code, name, description)
VALUES
    ('superadmin', 'Super Administrator', 'Administrative user for all locations.'),
    ('admin', 'Administrator', 'Administrative user for a location.'),
    ('staff', 'Staff', 'Staff user assigned to a location.'),
    ('customer', 'Customer', 'Customer user assigned to a location.');
