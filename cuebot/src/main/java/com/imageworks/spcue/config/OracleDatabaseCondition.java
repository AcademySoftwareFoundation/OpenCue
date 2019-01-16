package com.imageworks.spcue.config;

import org.springframework.context.annotation.Condition;
import org.springframework.context.annotation.ConditionContext;
import org.springframework.core.type.AnnotatedTypeMetadata;

public class OracleDatabaseCondition implements Condition {

    @Override
    public boolean matches(ConditionContext context, AnnotatedTypeMetadata metadata) {
        String dbEngine = System.getenv("CUEBOT_DB_ENGINE");
        if (dbEngine == null) {
            return false;
        }
        DatabaseEngine selectedDatabaseEngine = DatabaseEngine.valueOf(dbEngine.toUpperCase());
        return selectedDatabaseEngine.equals(DatabaseEngine.ORACLE);
    }

}
