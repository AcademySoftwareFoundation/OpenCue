package com.imageworks.spcue.dao.criteria;

import java.util.Set;

import com.imageworks.common.SpiIce.IntegerSearchCriterion;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;

public interface ProcSearchGeneratorInterface extends CriteriaGeneratorInterface {
    void addDurationRange(IntegerSearchCriterion criterion);
    Phrase notJob(JobInterface job);
    Phrase notGroup(GroupInterface group);
    void buildWhereClause(ProcSearchCriteria criteria, Set<Phrase> notJobs, Set<Phrase> notGroups);
    void filterByHost(HostInterface host);
    void sortByHostName();
    void sortByDispatchedTime();
    void sortByBookedTime();
}
