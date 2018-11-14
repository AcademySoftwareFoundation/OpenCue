package com.imageworks.spcue.dao.criteria;

import java.util.List;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.config.DatabaseEngine;
import com.imageworks.spcue.dao.criteria.postgres.FrameSearchGenerator;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;

public class FrameSearchFactory extends CriteriaFactory {
    private DatabaseEngine dbEngine;

    public FrameSearch create(List<String> list) {
        return new FrameSearch(getFrameSearchGenerator(), list);
    }

    public FrameSearch create(JobInterface job) {
        return new FrameSearch(getFrameSearchGenerator(), job);
    }

    public FrameSearch create(FrameInterface frame) {
        return new FrameSearch(getFrameSearchGenerator(), frame);
    }

    public FrameSearch create(JobInterface job, FrameSearchCriteria criteria) {
        return new FrameSearch(getFrameSearchGenerator(), job, criteria);
    }

    public FrameSearch create(LayerInterface layer) {
        return new FrameSearch(getFrameSearchGenerator(), layer);
    }

    public FrameSearch create(LayerInterface layer, FrameSearchCriteria criteria) {
        return new FrameSearch(getFrameSearchGenerator(), layer, criteria);
    }

    private FrameSearchGeneratorInterface getFrameSearchGenerator() {
        if (dbEngine.equals(DatabaseEngine.POSTGRES)) {
            return new FrameSearchGenerator();
        } else if (dbEngine.equals(DatabaseEngine.ORACLE)) {
            return new com.imageworks.spcue.dao.criteria.oracle.FrameSearchGenerator();
        } else {
            throw new RuntimeException(
                    "current database engine is not supported by HostSearchFactory");
        }
    }

    public DatabaseEngine getDbEngine() {
        return dbEngine;
    }

    public void setDbEngine(DatabaseEngine dbEngine) {
        this.dbEngine = dbEngine;
    }
}
