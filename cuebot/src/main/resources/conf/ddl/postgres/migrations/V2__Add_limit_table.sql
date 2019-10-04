
-- Create a table to keep track of arbitrary limits
CREATE TABLE limit_record (
    pk_limit_record VARCHAR(36) NOT NULL,
    str_name VARCHAR(255) NOT NULL,
    int_max_value INT,
    b_host_limit BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE layer_limit (
    pk_layer_limit VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_limit_record VARCHAR(36) NOT NULL
);

-- Remove the layer_limit history to keep the table clean.
CREATE FUNCTION trigger__before_delete_layer_drop_limit()
RETURNS TRIGGER AS $body$
BEGIN
    DELETE FROM layer_limit where pk_layer=OLD.pk_layer;
    RETURN OLD;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER before_delete_layer_drop_limit BEFORE DELETE ON layer
FOR EACH ROW
    EXECUTE PROCEDURE trigger__before_delete_layer_drop_limit();
