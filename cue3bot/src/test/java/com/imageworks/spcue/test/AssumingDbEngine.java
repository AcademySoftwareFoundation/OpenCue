package com.imageworks.spcue.test;

import org.junit.rules.TestRule;
import org.junit.runner.Description;
import org.junit.runners.model.Statement;

import com.imageworks.spcue.config.DatabaseEngine;

public class AssumingDbEngine implements TestRule {

    private DatabaseEngine dbEngine;

    public AssumingDbEngine(DatabaseEngine dbEngine) {
        this.dbEngine = dbEngine;
    }

    @Override
    public Statement apply(Statement base, Description description) {
        return new Statement() {
            @Override
            public void evaluate() throws Throwable {
                System.out.println(dbEngine.toString());
            }
        };
    }
}
