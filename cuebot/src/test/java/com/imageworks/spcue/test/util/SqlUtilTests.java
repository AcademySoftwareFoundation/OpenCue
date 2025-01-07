package com.imageworks.spcue.test.util;

import org.junit.Test;

import static com.imageworks.spcue.util.SqlUtil.buildBindVariableArray;
import static org.junit.Assert.assertEquals;

public class SqlUtilTests {

    @Test
    public void testBuildBindVariableArray() {
        String colName = "arbitrary-column-name";

        String queryString = buildBindVariableArray(colName, 6);

        assertEquals(colName + " IN (?,?,?,?,?,?)", queryString);
    }
}
