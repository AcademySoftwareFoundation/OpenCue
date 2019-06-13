package com.imageworks.spcue.dao;

import com.imageworks.spcue.service.DependManagerService;
import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceUtils;
import org.springframework.util.Assert;

import javax.sql.DataSource;
import java.sql.Connection;

public class AbstractJdbcDao {

    protected DataSource dataSource;

    protected JdbcTemplate jdbcTemplate;

    @Autowired
    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
        this.jdbcTemplate = new JdbcTemplate(dataSource);
    }

    public JdbcTemplate getJdbcTemplate() {
        return jdbcTemplate;
    }

    protected final Connection getConnection() throws CannotGetJdbcConnectionException {
        Assert.state(dataSource != null, "No DataSource set");
        return DataSourceUtils.getConnection(dataSource);
    }

    protected final Logger logger = Logger.getLogger(this.getClass());

}
