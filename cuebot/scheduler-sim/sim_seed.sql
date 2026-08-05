-- Deterministic base seed for the scheduler simulator (one-time install data).
-- Facility 'sim' (default), allocation 'sim.general' (default, tag general),
-- show 'sim' with its root folder/point, and a subscription with a huge burst
-- so the show is never the bottleneck. Department 'Unknown' comes from
-- seed_data.sql (pk AAAAAAAA-...-AAA7).

BEGIN;

-- Clean any prior partial 'sim' entities (from earlier gRPC attempts).
DELETE FROM subscription WHERE pk_show IN (SELECT pk_show FROM show WHERE str_name='sim');
DELETE FROM subscription WHERE pk_alloc IN (
    SELECT pk_alloc FROM alloc WHERE pk_facility IN (
        SELECT pk_facility FROM facility WHERE str_name='sim'));
DELETE FROM point  WHERE pk_show IN (SELECT pk_show FROM show WHERE str_name='sim');
DELETE FROM folder WHERE pk_show IN (SELECT pk_show FROM show WHERE str_name='sim');
DELETE FROM show_stats WHERE pk_show IN (SELECT pk_show FROM show WHERE str_name='sim');
DELETE FROM show WHERE str_name='sim';
DELETE FROM alloc WHERE pk_facility IN (SELECT pk_facility FROM facility WHERE str_name='sim');
DELETE FROM alloc WHERE str_name='sim.general';
DELETE FROM facility WHERE str_name='sim';

INSERT INTO facility (pk_facility, str_name, b_default) VALUES
    ('10000000-0000-0000-0000-000000000001', 'sim', false);

INSERT INTO alloc (pk_alloc, str_name, b_allow_edit, b_default, str_tag, pk_facility, b_billable, b_enabled) VALUES
    ('10000000-0000-0000-0000-000000000002', 'sim.general', true, false, 'general',
     '10000000-0000-0000-0000-000000000001', false, true);

INSERT INTO show (pk_show, str_name, int_default_max_cores, int_default_min_cores, b_booking_enabled, b_dispatch_enabled, b_active) VALUES
    ('10000000-0000-0000-0000-000000000003', 'sim', 20000000, 100, true, true, true);

INSERT INTO show_stats (pk_show, int_frame_insert_count, int_job_insert_count, int_frame_success_count, int_frame_fail_count) VALUES
    ('10000000-0000-0000-0000-000000000003', 0, 0, 0, 0);

INSERT INTO folder (pk_folder, pk_parent_folder, pk_show, str_name, b_default, pk_dept, int_job_min_cores, int_job_max_cores, int_job_priority, f_order, b_exclude_managed) VALUES
    ('10000000-0000-0000-0000-000000000004', null, '10000000-0000-0000-0000-000000000003', 'sim', true,
     'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA7', -1, -1, -1, 1, false);

INSERT INTO point (pk_point, pk_dept, pk_show, str_ti_task, int_cores, b_managed, int_min_cores, float_tier) VALUES
    ('10000000-0000-0000-0000-000000000005', 'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA7', '10000000-0000-0000-0000-000000000003', null, 0, false, 0, 0);

-- Huge burst (core-points): the show can use the whole farm and then some.
INSERT INTO subscription (pk_subscription, pk_alloc, pk_show, int_size, int_burst, int_cores, float_tier) VALUES
    ('10000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000003', 5724800, 1000000000, 0, 0);

COMMIT;
