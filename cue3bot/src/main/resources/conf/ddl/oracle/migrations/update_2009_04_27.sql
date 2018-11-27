
/**
* Add a layer sort column to the frame table
**/
ALTER TABLE frame ADD int_layer_order NUMERIC(16,0);

/**
* Populate it with current values
**/
UPDATE frame SET int_layer_order = (SELECT int_dispatch_order FROM layer WHERE frame.pk_layer = layer.pk_layer);

/**
* Now that the index is made, update the new column to be not 
**/
ALTER TABLE frame MODIFY (int_layer_order NUMERIC(16,0) NOT NULL);

/**
* Create a composite index with the frame and layer dispatch order
**/
CREATE INDEX i_frame_dispatch_idx ON frame (int_dispatch_order, int_layer_order);

/**
* With the composite index we no longer need this index
**/
DROP INDEX I_FRAME_INTDISPATCHORDER;

