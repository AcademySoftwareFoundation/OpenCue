-- Deferred layer booking: no frame of a layer may start before ts_start_after.
-- Written by the automatic license-shortage backoff and by the SetStartAfter RPC.
-- str_start_after_reason is free text displayed verbatim in tooling.

ALTER TABLE layer
    ADD COLUMN ts_start_after TIMESTAMP (6) WITH TIME ZONE DEFAULT NULL,
    ADD COLUMN str_start_after_reason VARCHAR(255) DEFAULT NULL;

-- Almost every row is NULL, so the partial index is tiny. It serves the
-- cuebot_layers_delayed gauge and any "which layers are delayed" query.
CREATE INDEX i_layer_start_after ON layer (ts_start_after)
    WHERE ts_start_after IS NOT NULL;
