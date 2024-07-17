-- Add a serial column to layer_output for getting correct order of outputs

alter table layer_output add ser_order SERIAL not null;
