
CREATE TABLE service (
    pk_service          VARCHAR2(36) NOT NULL,
    str_name            VARCHAR2(36) NOT NULL,
    b_threadable        NUMERIC(1,0) NOT NULL,
    int_cores_min       NUMERIC(8,0) NOT NULL,    
    int_mem_min         NUMERIC(16,0) NOT NULL,
    str_tags            VARCHAR2(128) NOT NULL
);

ALTER TABLE service
    ADD CONSTRAINT c_pk_service PRIMARY KEY (pk_service);
CREATE UNIQUE INDEX i_service_str_name ON service (str_name);

INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0','default', 0, 100, 3355443, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1','prman', 0, 100, 3355443, 'general | desktop'); 
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA2','arnold', 1, 100, 3355443, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA3','shell', 0, 50, 1048576, 'util');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA4','maya', 0, 100, 1048576 * 2, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA5','houdini', 0, 100, 3355443, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA6','svea', 1, 100, 3355443, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA7','katana', 1, 100, 3355443, 'general | desktop | util');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA8','shake', 0, 100, 3355443, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA9','nuke', 0, 100, 1048576 * 2, 'general | desktop');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAA10','ginsu', 0, 50, 1048576 / 2, 'general | desktop | util');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAA11','preprocess', 0, 10, 524288, 'util');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAA12','postprocess', 0, 10, 524288, 'util');
INSERT INTO service VALUES ('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAA13','tango', 1, 200, 3355443, 'general | desktop');


ALTER TABLE layer ADD str_services VARCHAR2(128) DEFAULT 'default' NOT NULL;
