package com.imageworks.spcue.dao.criteria;

import java.util.List;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;

public interface FrameSearchInterface extends CriteriaInterface {
    FrameSearchCriteria getCriteria();
    void setCriteria(FrameSearchCriteria criteria);
    JobInterface getJob();
    String getSortedQuery(String query);
    void filterByFrameIds(List<String> frameIds);
    void filterByJob(JobInterface job);
    void filterByFrame(FrameInterface frame);
    void filterByLayer(LayerInterface layer);
    void filterByLayers(List<LayerInterface> layers);
    void filterByFrameStates(List<FrameState> frameStates);
    void filterByFrameSet(String frameSet);
    void filterByMemoryRange(String range);
    void filterByDurationRange(String range);
    void filterByChangeDate(int changeDate);
}
