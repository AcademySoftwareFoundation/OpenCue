package com.imageworks.spcue.dao.criteria;

import java.util.List;

import com.imageworks.common.SpiIce.IntegerSearchCriterion;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;

public interface ProcSearchInterface extends CriteriaInterface {
    ProcSearchCriteria getCriteria();
    void setCriteria(ProcSearchCriteria criteria);
    void notJobs(List<JobInterface> jobs);
    void notGroups(List<GroupInterface> groups);
    void addDurationRange(IntegerSearchCriterion criterion);
    void filterByHost(HostInterface host);
    void sortByHostName();
    void sortByDispatchedTime();
    void sortByBookedTime();
}
