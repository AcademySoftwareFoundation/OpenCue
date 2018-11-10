package com.imageworks.spcue.dao.criteria;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;

public class HostSearchFactory extends CriteriaFactory {
    public HostSearchInterface create(HostSearchCriteria criteria) {
        return new HostSearch(criteria);
    }

    public HostSearchInterface create(AllocationEntity allocEntity) {
        // TODO HostSearch probably doesn't need this as a static method since we have this
        // factory now.
        return HostSearch.byAllocation(allocEntity);
    }
}
