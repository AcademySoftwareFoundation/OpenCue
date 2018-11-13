package com.imageworks.spcue.dao.criteria.postgres;

import java.util.HashSet;
import java.util.Set;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.dao.criteria.HostSearchGeneratorInterface;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;

public class HostSearchGenerator implements HostSearchGeneratorInterface {
    private final CriteriaGenerator criteriaGenerator;

    public HostSearchGenerator(CriteriaGenerator criteriaGenerator) {
        this.criteriaGenerator = criteriaGenerator;
    }

    public void filterByAlloc(AllocationInterface alloc) {
        criteriaGenerator.addPhrase("host.pk_alloc", alloc.getAllocationId());
    }

    public void buildWhereClause(HostSearchCriteria criteria) {
        criteriaGenerator.addPhrase("host.pk_host", criteria.getIdsList());
        criteriaGenerator.addPhrase("host.str_name", criteria.getHostsList());
        criteriaGenerator.addPhrase("host.str_name", new HashSet<>(criteria.getSubstrList()));
        criteriaGenerator.addRegexPhrase("host.str_name", new HashSet<>(criteria.getRegexList()));
        criteriaGenerator.addPhrase("alloc.str_name", criteria.getAllocsList());
        Set<String> items = new HashSet<String>(criteria.getStates().getStateCount());
        for (HardwareState w: criteria.getStates().getStateList()) {
            items.add(w.toString());
        }
        criteriaGenerator.addPhrase("host_stat.str_state", items);
    }
}
