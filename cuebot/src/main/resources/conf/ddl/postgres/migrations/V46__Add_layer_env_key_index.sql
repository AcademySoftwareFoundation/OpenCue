-- Live application licensing (CUE_LICENSES) reads layer_env by key on hot paths:
--   * LicenseSource.readInFlight scans running licensed frames per budget snapshot
--   * LicenseBookingGate.licensesForLayer resolves a layer's declaration (cached)
--   * LicenseBookingGate.findPackableJobs finds pending licensed work to pack
-- layer_env previously had no index on str_key, so those queries could only seq
-- scan a table holding every environment variable of every live layer.
CREATE INDEX i_layer_env_str_key ON layer_env (str_key, pk_layer);
