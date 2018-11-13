package com.imageworks.spcue.dao.criteria;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;

public interface HostSearchGeneratorInterface {
    void filterByAlloc(AllocationInterface alloc);
    void buildWhereClause(HostSearchCriteria criteria);
}
