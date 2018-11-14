package com.imageworks.spcue.dao.criteria.oracle;

import java.util.HashSet;
import java.util.Set;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.dao.criteria.HostSearchGeneratorInterface;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;

public class HostSearchGenerator extends CriteriaGenerator implements HostSearchGeneratorInterface {

    public void filterByAlloc(AllocationInterface alloc) {
        addPhrase("host.pk_alloc", alloc.getAllocationId());
    }

    public void buildWhereClause(HostSearchCriteria criteria) {
        addPhrase("host.pk_host", criteria.getIdsList());
        addPhrase("host.str_name", criteria.getHostsList());
        addPhrase("host.str_name", new HashSet<>(criteria.getSubstrList()));
        addRegexPhrase("host.str_name", new HashSet<>(criteria.getRegexList()));
        addPhrase("alloc.str_name", criteria.getAllocsList());
        Set<String> items = new HashSet<String>(criteria.getStates().getStateCount());
        for (HardwareState w: criteria.getStates().getStateList()) {
            items.add(w.toString());
        }
        addPhrase("host_stat.str_state", items);
    }
}
