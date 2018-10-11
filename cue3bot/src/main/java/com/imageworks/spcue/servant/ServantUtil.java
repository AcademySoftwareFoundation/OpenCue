
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue.servant;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.CueClientIce.AllocationInterfacePrx;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrx;
import com.imageworks.spcue.CueClientIce.HostInterfacePrx;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.LayerInterfacePrx;
import com.imageworks.spcue.CueClientIce.SubscriptionInterfacePrx;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerSeq;

public class ServantUtil {

    public static AllocationInterface convertAllocationProxy(final AllocationInterfacePrx prx) {
        return new AllocationInterface() {
            String _id = prx.ice_getIdentity().name;
            public String getAllocationId() { return _id; }
            public String getId() { return _id; }
            public String getName() { throw new RuntimeException("not implemented"); }
            public String getFacilityId() { throw new RuntimeException("not implemented"); }
        };
    }

    public static List<AllocationInterface> convertAllocationProxyList(List<AllocationInterfacePrx> allocs)  {
        final List<AllocationInterface> result = new ArrayList<AllocationInterface>();
        for (final AllocationInterfacePrx proxy: allocs) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new AllocationInterface() {
                String _id = id;
                public String getAllocationId() { return _id; }
                public String getId() { return _id; }
                public String getName() { throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;
    }

    public static List<SubscriptionInterface> convertSubscriptionProxyList(List<SubscriptionInterfacePrx> subs)  {
        final List<SubscriptionInterface> result = new ArrayList<SubscriptionInterface>();
        for (final SubscriptionInterfacePrx proxy: subs) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new SubscriptionInterface() {
                String _id = id;
                public String getSubscriptionId() { return _id; }
                public String getId() {  return _id; }
                public String getShowId() { throw new RuntimeException("not implemented"); }
                public String getName() { throw new RuntimeException("not implemented"); }
                public String getAllocationId() { throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }

            });
        }
        return result;
    }

    public static List<JobInterface> convertJobProxyList(List<JobInterfacePrx> jobs) {
        final List<JobInterface> result = new ArrayList<JobInterface>();
        for (final JobInterfacePrx proxy: jobs) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new JobInterface() {
                String _id = id;
                public String getJobId() { return _id; }
                public String getShowId() {  throw new RuntimeException("not implemented"); }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;
    }

    public static List<GroupInterface> convertGroupProxyList(List<GroupInterfacePrx> groups) {
        final List<GroupInterface> result = new ArrayList<GroupInterface>();
        for (final GroupInterfacePrx proxy: groups) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new GroupInterface() {
                String _id = id;
                public String getShowId() {  throw new RuntimeException("not implemented"); }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getGroupId() { return _id; }
            });
        }
        return result;
    }

    public static List<LayerInterface> convertLayerProxyList(List<LayerInterfacePrx> layers) {
        final List<LayerInterface> result = new ArrayList<LayerInterface>();
        for (final LayerInterfacePrx proxy: layers) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new LayerInterface() {
                String _id = id;
                public String getLayerId() { return _id; }
                public String getJobId() {  throw new RuntimeException("not implemented"); }
                public String getShowId() {  throw new RuntimeException("not implemented"); }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;
    }

    public static List<LayerInterface> convertLayerFilterList(LayerSeq layers) {
        final List<LayerInterface> result = new ArrayList<LayerInterface>();
        for (final Layer layer: layers.getLayersList()) {
            final String id = layer.getId();
            result.add(new LayerInterface() {
                String _id = id;
                public String getLayerId() { return _id; }
                public String getJobId() {  throw new RuntimeException("not implemented"); }
                public String getShowId() {  throw new RuntimeException("not implemented"); }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;
    }

    public static GroupInterface convertGroupProxy(GroupInterfacePrx proxy) {
        final String id = proxy.ice_getIdentity().name;
        return new GroupInterface() {
            String _id = id;
            public String getShowId() {  throw new RuntimeException("not implemented"); }
            public String getId() { return _id; }
            public String getName() {  throw new RuntimeException("not implemented"); }
            public String getGroupId() { return _id; }
        };
    }

    public static List<String> convertProxyListToUniqueList(Collection<?> proxies) {
        List<String> result = new ArrayList<String>(proxies.size());
        for (Object p: proxies) {
            Ice.ObjectPrx proxy = (Ice.ObjectPrx) p;
            result.add(proxy.ice_getIdentity().name);
        }
        return result;
    }

    public static List<HostInterface> convertHostProxyList(List<HostInterfacePrx> hosts) {
        final List<HostInterface> result = new ArrayList<HostInterface>(hosts.size());
        for (final HostInterfacePrx proxy: hosts) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new HostInterface() {
                String _id = id;
                public String getHostId() { return _id; }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getAllocationId() {  throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;

    }


}

