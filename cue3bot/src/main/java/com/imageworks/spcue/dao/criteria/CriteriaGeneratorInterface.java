package com.imageworks.spcue.dao.criteria;

import java.util.List;

public interface CriteriaGeneratorInterface {
    String generateWhereClause(List<StringBuilder> chunks);
    String queryWithPaging(
            String query, int firstResult, int maxResults, List<Sort> order);
}
