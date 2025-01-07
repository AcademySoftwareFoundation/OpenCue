package com.imageworks.spcue.config;

public enum DatabaseEngine {
    POSTGRES;

    public static DatabaseEngine fromEnv() {
        return POSTGRES;
    }
}
