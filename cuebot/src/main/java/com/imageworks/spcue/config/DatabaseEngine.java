package com.imageworks.spcue.config;

public enum DatabaseEngine {
    ORACLE,
    POSTGRES;

    public static DatabaseEngine fromEnv() {
        String envValue = System.getenv("CUEBOT_DB_ENGINE");
        if (envValue == null) {
            return POSTGRES;
        }
        return DatabaseEngine.valueOf(envValue.toUpperCase());
    }
}
