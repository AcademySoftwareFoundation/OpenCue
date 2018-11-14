package com.imageworks.spcue.dao.criteria;

import java.util.List;

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;

public interface FrameSearchGeneratorInterface extends CriteriaGeneratorInterface {
    String getSortedQuery(String query, int page, int limit);
    void addFrameStates(List<FrameState> s);
    void addFrameSet(String frameSet);
    void addMemoryRange(String range);
    void addDurationRange(String range);
    void addChangeDate(int changeDate);
    void addLayers(List<LayerInterface> layers);
    void buildWhereClause(FrameSearchCriteria criteria, JobInterface job, LayerInterface layer);
}
