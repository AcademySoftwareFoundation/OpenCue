-- Add limit index
CREATE INDEX i_layer_limit_pk_layer ON layer_limit (pk_layer);
CREATE INDEX i_layer_limit_pk_limit_record ON layer_limit (pk_limit_record);
CREATE INDEX i_limit_record_pk_limit_record ON limit_record (pk_limit_record);
