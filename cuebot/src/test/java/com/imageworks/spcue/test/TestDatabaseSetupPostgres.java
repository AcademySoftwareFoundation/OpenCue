/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.test;

import com.google.common.base.Charsets;
import com.google.common.io.Resources;
import io.zonky.test.db.postgres.embedded.EmbeddedPostgres;
import org.flywaydb.core.Flyway;

import java.net.URL;
import java.sql.Connection;
import java.sql.Statement;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

public final class TestDatabaseSetupPostgres {
    private static final String DB_NAME = "postgres";
    private static final String USERNAME = "postgres";
    private static AtomicBoolean setupComplete = new AtomicBoolean(false);
    private EmbeddedPostgres postgres;

    public TestDatabaseSetupPostgres() {}

    public String getUrl() {
        return postgres.getJdbcUrl(USERNAME, DB_NAME);
    }

    public String getUsername() {
        return USERNAME;
    }

    public String getPassword() {
        return null;
    }

    public void create() throws Exception {
        if (!setupComplete.compareAndSet(false, true)) {
            return;
        }

        postgres = EmbeddedPostgres.start();
        Flyway flyway = Flyway.configure().dataSource(postgres.getPostgresDatabase())
                .locations("classpath:conf/ddl/postgres/migrations").load();
        flyway.migrate();

        populateTestData();
    }

    private void populateTestData() throws Exception {
        Connection conn = postgres.getPostgresDatabase().getConnection();

        URL url = Resources.getResource("conf/ddl/postgres/test_data.sql");
        List<String> testDataStatements = Resources.readLines(url, Charsets.UTF_8);
        for (String testDataStatement : testDataStatements) {
            Statement st = conn.createStatement();
            st.execute(testDataStatement);
            st.close();
        }

        conn.close();
    }
}
