-- Maestro reads each planned layer's next waiting frames once per tick, in
-- dispatch order with a LIMIT (DispatchQuery.FIND_DISPATCH_FRAMES_BY_LAYER).
-- This index serves that read as an ordered scan that stops at the limit,
-- instead of a scan and sort of every waiting frame of the layer.
--
-- On a large production frame table, build it out-of-band with
-- CREATE INDEX CONCURRENTLY (not allowed inside Flyway's transaction) and
-- mark this migration applied, so writes to frame are not blocked meanwhile.
CREATE INDEX IF NOT EXISTS i_frame_layer_dispatch_waiting
    ON frame (pk_layer, int_dispatch_order, int_layer_order)
    WHERE str_state = 'WAITING';
