package com.imageworks.spcue.dao.criteria;

import java.util.List;

public interface CriteriaGeneratorInterface {
    String generateWhereClause();
    String queryWithPaging(String query, int firstResult, int maxResults, List<Sort> order);
    List<Object> getValues();
}
