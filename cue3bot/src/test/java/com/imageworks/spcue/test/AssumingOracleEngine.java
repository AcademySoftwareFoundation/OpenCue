package com.imageworks.spcue.test;

import org.junit.AssumptionViolatedException;
import org.junit.rules.TestRule;
import org.junit.runner.Description;
import org.junit.runners.model.Statement;

import com.imageworks.spcue.config.DatabaseEngine;

public class AssumingOracleEngine implements TestRule {

    private DatabaseEngine dbEngine;

    public AssumingOracleEngine() {}

    @Override
    public Statement apply(Statement base, Description description) {
        return new Statement() {
            @Override
            public void evaluate() throws Throwable {
                if (dbEngine == DatabaseEngine.ORACLE) {
                    base.evaluate();
                } else {
                    throw new AssumptionViolatedException(
                            "Current database engine is " + dbEngine.toString() +
                            ", test requires ORACLE. Skipping");
                }
            }
        };
    }

    public DatabaseEngine getDbEngine() {
        return dbEngine;
    }

    public void setDbEngine(DatabaseEngine dbEngine) {
        this.dbEngine = dbEngine;
    }
}
