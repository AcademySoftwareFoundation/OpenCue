-- Set the variable at the beginning
DO $$
DECLARE
    test_prefix TEXT := 'your_prefix_here'; -- Replace 'your_prefix_here' with your actual prefix
BEGIN
    -- Delete proc (references frames)
    DELETE FROM proc WHERE pk_frame IN (
        SELECT f.pk_frame FROM frame f
        JOIN layer l ON f.pk_layer = l.pk_layer
        JOIN job j ON f.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete frame_history (references frames)
    DELETE FROM frame_history WHERE pk_frame IN (
        SELECT f.pk_frame FROM frame f
        JOIN layer l ON f.pk_layer = l.pk_layer
        JOIN job j ON f.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete frames (references layers)
    DELETE FROM frame WHERE pk_frame IN (
        SELECT f.pk_frame FROM frame f
        JOIN layer l ON f.pk_layer = l.pk_layer
        JOIN job j ON f.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_output (references layers)
    DELETE FROM layer_output WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_env (references layers)
    DELETE FROM layer_env WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_mem (references layers)
    DELETE FROM layer_mem WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_usage (references layers)
    DELETE FROM layer_usage WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_stat (references layers)
    DELETE FROM layer_stat WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_resource (references layers)
    DELETE FROM layer_resource WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layer_history (references layers)
    DELETE FROM layer_history WHERE pk_layer IN (
        SELECT l.pk_layer FROM layer l
        JOIN job j ON l.pk_job = j.pk_job
        WHERE j.str_name LIKE test_prefix || '%'
    );

    -- Delete layers (references jobs)
    DELETE FROM layer WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_local (references jobs and hosts)
    DELETE FROM job_local WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_env (references jobs)
    DELETE FROM job_env WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_mem (references jobs)
    DELETE FROM job_mem WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_usage (references jobs)
    DELETE FROM job_usage WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_stat (references jobs)
    DELETE FROM job_stat WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_resource (references jobs)
    DELETE FROM job_resource WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_post (references jobs)
    DELETE FROM job_post WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete job_history (references jobs)
    DELETE FROM job_history WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete depend (references jobs)
    DELETE FROM depend WHERE pk_job_depend_on IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    ) OR pk_job_depend_er IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete comments (references jobs)
    DELETE FROM comments WHERE pk_job IN (
        SELECT pk_job FROM job WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete jobs (references folders/shows/facilities/depts)
    DELETE FROM job WHERE str_name LIKE test_prefix || '%';

    -- Delete host_local (references hosts)
    DELETE FROM host_local WHERE pk_host IN (
        SELECT pk_host FROM host WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete host_tag (references hosts)
    DELETE FROM host_tag WHERE pk_host IN (
        SELECT pk_host FROM host WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete host_stat (references hosts)
    DELETE FROM host_stat WHERE pk_host IN (
        SELECT pk_host FROM host WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete deed (references hosts and owners)
    DELETE FROM deed WHERE pk_host IN (
        SELECT pk_host FROM host WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete hosts (references allocations)
    DELETE FROM host WHERE str_name LIKE test_prefix || '%';

    -- Delete owner (references shows)
    DELETE FROM owner WHERE pk_show IN (
        SELECT pk_show FROM show WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete folder_resource (references folders)
    DELETE FROM folder_resource WHERE pk_folder IN (
        SELECT pk_folder FROM folder WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete folders (references shows and depts)
    DELETE FROM folder WHERE str_name LIKE test_prefix || '%';

    -- Delete subscriptions (references allocations and shows)
    DELETE FROM subscription WHERE pk_alloc IN (
        SELECT pk_alloc FROM alloc WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete allocations (references facilities)
    DELETE FROM alloc WHERE str_name LIKE test_prefix || '%';

    -- Delete show_service (references shows)
    DELETE FROM show_service WHERE pk_show IN (
        SELECT pk_show FROM show WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete show_alias (references shows)
    DELETE FROM show_alias WHERE pk_show IN (
        SELECT pk_show FROM show WHERE str_name LIKE test_prefix || '%'
    );

    -- Delete shows
    DELETE FROM show WHERE str_name LIKE test_prefix || '%';

    -- Delete departments
    DELETE FROM dept WHERE str_name LIKE test_prefix || '%';

    -- Delete facilities
    DELETE FROM facility WHERE str_name LIKE test_prefix || '%';

END $$;
