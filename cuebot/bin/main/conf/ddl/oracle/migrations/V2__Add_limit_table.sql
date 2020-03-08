
CREATE TABLE "LIMIT_RECORD" (
    "PK_LIMIT_RECORD" VARCHAR2(36 BYTE) NOT NULL,
    "STR_NAME" VARCHAR2(255 BYTE) NOT NULL,
    "INT_MAX_VALUE" NUMBER(38,0) DEFAULT 0 NOT NULL,
    "B_HOST_LIMIT" NUMBER(1,0) DEFAULT 0 NOT NULL
);

CREATE TABLE "LAYER_LIMIT" (
    "PK_LAYER_LIMIT" VARCHAR2(36 BYTE) NOT NULL,
    "PK_LAYER" VARCHAR2(36 BYTE) NOT NULL,
    "PK_LIMIT_RECORD" VARCHAR2(36 BYTE) NOT NULL
);

CREATE TRIGGER "BEFORE_DELETE_LAYER_DROP_LIMIT" BEFORE DELETE ON layer
FOR EACH ROW
BEGIN
    DELETE FROM layer_limit WHERE pk_layer=:old.pk_layer;
END;
