
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

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Scanner;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class TestDatabaseSetup {
    private static final String USERNAME = "test";
    private static final String PASSWORD = "c0r0na";
    private String sysPwd;
    private String dbTns;

    // private static final String USERNAME = "ct" + System.currentTimeMillis();
    // private static final String PASSWORD = "password";
    private static AtomicBoolean setupComplete = new AtomicBoolean(false);

    public TestDatabaseSetup() {
        String tns = System.getenv("CUEBOT_DB_TNS");
        if (tns != null) {
            setDbTns(tns);
        }
        String pwd = System.getenv("CUEBOT_DB_SYS_PWD");
        if (pwd != null) {
            setSysPwd(pwd);
        }
    }

    private String getDbTns() {
        return dbTns;
    }

    private void setDbTns(String dbTns) {
        this.dbTns = dbTns;
    }

    private String getSysPwd() {
        return sysPwd;
    }

    private void setSysPwd(String sysPwd) {
        this.sysPwd = sysPwd;
    }

    public String getUsername() {
        return USERNAME;
    }

    public String getPassword() {
        return PASSWORD;
    }

    public void create() throws Exception  {
        if (!setupComplete.compareAndSet(false, true)) {
            return;
        }

        System.setProperty("oracle.net.tns_admin", System.getenv("TNS_ADMIN"));
        System.out.println("CREATING CUE3 TEST USER");
        Connection sysConn = DriverManager.getConnection(
            "jdbc:oracle:oci:@" + getDbTns(),
            "sys as sysdba",
            getSysPwd()
        );

        purgeOldUsers(sysConn);

        Statement stmt = null;
        try {
            stmt = sysConn.createStatement();
            stmt.execute("CREATE USER " + USERNAME + " IDENTIFIED BY " + PASSWORD);
            stmt.execute("GRANT CONNECT, RESOURCE, DBA TO " + USERNAME);
        } finally {
            if (stmt != null) {
                stmt.close();
            }

            if (sysConn != null) {
                sysConn.close();
            }
        }
        
        // The spring junit runner doesn't want to call the destroy-method on this bean, even if we tell it to in the XML. As such,
        // we're adding a shutdown hook here to ensure that the database gets cleaned up. Newer version of spring have a class-level
        // @DirtiesContext annotation that you can use to tell spring to destroy everything after the test class runs.
        Runtime.getRuntime().addShutdownHook(new Thread() {
            @Override
            public void run() {
                // try {
                //     TestDatabaseSetup.this.destroy();
                // } catch (Exception e) {
                //     e.printStackTrace();
                // }
            }

        });

        System.out.println("CREATING CUE3 TEST DATABASE " + USERNAME);
        Connection conn = DriverManager.getConnection(
            "jdbc:oracle:oci:@" + getDbTns(),
            USERNAME,
            PASSWORD
        );
        stmt = null;
        try {
            stmt = conn.createStatement();

            // http://stackoverflow.com/a/18897411
            String dbCreateScript = new Scanner(new File("src/test/resources/conf/ddl/unittest-db-setup.sql"), "UTF-8").useDelimiter("\\A").next();
            String[] dbCreateScriptPieces = dbCreateScript.split("-- SPLIT HERE!");

            for (String dbCreateScriptPiece : dbCreateScriptPieces) {
                System.out.print(".");
                try {
                    stmt.execute(dbCreateScriptPiece);
                } catch (Exception e) {
                    System.out.println(dbCreateScriptPiece);
                    throw e;
                }
            }
            System.out.println();
        } finally {
            if (stmt != null) {
                stmt.close();
            }

            if (conn != null) {
                conn.close();
            }
        }
    }

    public void destroy() throws Exception {
        System.out.println("DESTROYING CUE3 TEST DATABASE " + USERNAME);
        try (Connection conn = DriverManager.getConnection(
            "jdbc:oracle:oci:@" + getDbTns(),
            "sys as sysdba",
            getSysPwd()
        )) {
            purgeUser(conn, USERNAME);
        }
    }

    private void purgeOldUsers(Connection conn) throws SQLException {
        long EXPIRE_TIME = TimeUnit.MILLISECONDS.convert(6, TimeUnit.HOURS);
        long now = System.currentTimeMillis();
        Pattern ct_re = Pattern.compile("^CT(\\d+)$");

        try (
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(
                "SELECT username FROM dba_users WHERE username LIKE 'CT%'");
        ) {
            while (rs.next()) {
                String username = rs.getString(1);
                Matcher m = ct_re.matcher(username);
                if (!m.matches()) {
                    continue;
                }

                long ts = Long.valueOf(m.group(1));
                if (ts >= now - EXPIRE_TIME) {
                    System.out.println("FOUND NON-EXPIRED USER " + username);
                    continue;
                }

                System.out.println("REMOVING EXPIRED USER " + username);
                purgeUser(conn, username);
            }
        }
    }

    private void purgeUser(Connection conn, String username) throws SQLException {
        try (Statement rmstmt = conn.createStatement()) {
            rmstmt.execute("DROP USER " + username + " CASCADE");
        }
    }
}

