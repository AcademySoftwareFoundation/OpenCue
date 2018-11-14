package com.imageworks.spcue.dao.criteria;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;

public interface HostSearchInterface extends CriteriaInterface {
    HostSearchCriteria getCriteria();
    void filterByAlloc(AllocationInterface alloc);
}
