alter table job
    add b_loki_enabled bool;

alter table job
    add str_loki_url varchar(256);

