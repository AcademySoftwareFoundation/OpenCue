
CREATE TABLE show_service (
    pk_show_service     VARCHAR2(36) NOT NULL,
    pk_show             VARCHAR2(36) NOT NULL,
    str_name            VARCHAR2(36) NOT NULL,
    b_threadable        NUMERIC(1,0) NOT NULL,
    int_cores_min       NUMERIC(8,0) NOT NULL,    
    int_mem_min         NUMERIC(16,0) NOT NULL,
    str_tags            VARCHAR2(128) NOT NULL
);

ALTER TABLE show_service
    ADD CONSTRAINT c_pk_show_service PRIMARY KEY (pk_show_service);
CREATE UNIQUE INDEX i_show_service_str_name ON show_service (str_name, pk_show);

ALTER TABLE show_service ADD CONSTRAINT c_show_service_pk_show
    FOREIGN KEY (pk_show) REFERENCES show (pk_show);
