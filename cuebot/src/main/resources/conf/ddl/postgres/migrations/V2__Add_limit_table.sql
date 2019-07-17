
-- Create a table to keep track of arbitrary limits
CREATE TABLE limit_record (
    pk_limit_record VARCHAR(36) NOT NULL,
    str_name VARCHAR(255) NOT NULL,
    int_max_value INT
);

CREATE TABLE layer_limit (
    pk_layer_limit VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_limit_record VARCHAR(36) NOT NULL
);
