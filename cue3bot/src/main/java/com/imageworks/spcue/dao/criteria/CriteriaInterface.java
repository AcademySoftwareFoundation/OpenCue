package com.imageworks.spcue.dao.criteria;

import java.util.List;

public interface CriteriaInterface {
    String toString();
    void setFirstResult(int firstResult);
    void setMaxResults(int maxResults);
    void addSort(Sort o);
    String getWhereClause();
    String getQueryWithPaging(String query);
    List<Object> getValues();
    Object[] getValuesArray();
}
