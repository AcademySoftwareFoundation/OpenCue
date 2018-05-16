/**
* A table to store personal render farm hosts.
* b_interactive would be 0 if the user indicates they don't
* sit at the machine.
*
* Users cannot personal book machines they don't own.
*
**/
CREATE TABLE owner (
    pk_owner            VARCHAR2(36) NOT NULL,
    pk_show             VARCHAR2(36) NOT NULL,
    str_username        VARCHAR2(64) NOT NULL,
    ts_created          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    ts_updated          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);

ALTER TABLE owner
    ADD CONSTRAINT c_pk_owner PRIMARY KEY (pk_owner);

CREATE INDEX i_owner_pk_show ON owner (pk_show);
CREATE UNIQUE INDEX i_owner_str_username ON owner (str_username);
ALTER TABLE owner ADD CONSTRAINT c_owner_pk_show
    FOREIGN KEY (pk_show) REFERENCES show (pk_show);   

/**
* Owners can create configurations for hosts.
**/

CREATE TABLE deed (
    pk_deed             VARCHAR2(36) NOT NULL,
    pk_owner            VARCHAR2(36) NOT NULL,
    pk_host             VARCHAR2(36) NOT NULL,
    b_blackout          NUMBER(1,0) DEFAULT 0 NOT NULL,
    int_blackout_start  NUMBER(12,0),
    int_blackout_stop   NUMBER(12,0)
);

ALTER TABLE deed
    ADD CONSTRAINT c_pk_deed PRIMARY KEY (pk_deed);
       
CREATE UNIQUE INDEX i_deed_pk_host ON deed (pk_host);
CREATE INDEX i_deed_pk_owner ON deed (pk_owner);

ALTER TABLE deed ADD CONSTRAINT c_deed_pk_host
    FOREIGN KEY (pk_host) REFERENCES host (pk_host);
   

    
