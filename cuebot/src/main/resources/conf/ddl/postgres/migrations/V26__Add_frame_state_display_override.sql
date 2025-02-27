
-- Add table to hold frame status display overrides

CREATE TABLE frame_state_display_overrides (
    pk_frame_override VARCHAR(36) NOT NULL,
    pk_frame VARCHAR(36) NOT NULL,
    str_frame_state VARCHAR(24) NOT NULL,
    str_override_text VARCHAR(24) NOT NULL,
    str_rgb VARCHAR(24) NOT NULL
);

ALTER TABLE frame_state_display_overrides ADD CONSTRAINT c_frame_state_override UNIQUE
  (pk_frame, str_frame_state);

ALTER TABLE frame_state_display_overrides ADD CONSTRAINT c_frame_state_overrides_pk_frame
  FOREIGN KEY (pk_frame) REFERENCES frame (pk_frame);

