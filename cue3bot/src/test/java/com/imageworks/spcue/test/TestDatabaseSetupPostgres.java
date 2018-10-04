/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.imageworks.spcue.test;

import com.google.common.base.Charsets;
import com.google.common.io.Resources;
import ru.yandex.qatools.embed.postgresql.EmbeddedPostgres;

import java.net.URL;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.hamcrest.core.Is.is;
import static org.junit.Assert.assertThat;
import static ru.yandex.qatools.embed.postgresql.distribution.Version.Main.V10;

public final class TestDatabaseSetupPostgres {

    public static void main(String[] args) throws Exception {
        final EmbeddedPostgres postgres = new EmbeddedPostgres(V10);

        final String url = postgres.start("localhost", 5432, "cuebotfoo", "brian", "password");

        // connecting to a running Postgres and feeding up the database
        final Connection conn = DriverManager.getConnection(url);
        conn.createStatement().execute("CREATE TABLE films (code char(5));");
        conn.createStatement().execute("INSERT INTO films VALUES ('movie');");

        // ... or you can execute SQL files...
        //postgres.getProcess().importFromFile(new File("someFile.sql"))
        // ... or even SQL files with PSQL variables in them...
        //postgres.getProcess().importFromFileWithArgs(new File("someFile.sql"), "-v", "tblName=someTable")
        // ... or even restore database from dump file
        //postgres.getProcess().restoreFromFile(new File("src/test/resources/test.binary_dump"))

        // performing some assertions
        final Statement statement = conn.createStatement();
        assertThat(statement.execute("SELECT * FROM films;"), is(true));
        assertThat(statement.getResultSet().next(), is(true));
        assertThat(statement.getResultSet().getString("code"), is("movie"));

        conn.close();
        postgres.stop();
    }
}
