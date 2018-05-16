
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

import com.imageworks.spcue.Allocation;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.Subscription;
import com.imageworks.spcue.CueClientIce.AllocationInterfacePrx;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrx;
import com.imageworks.spcue.CueClientIce.HostInterfacePrx;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.LayerInterfacePrx;
import com.imageworks.spcue.CueClientIce.SubscriptionInterfacePrx;

public class ServantUtil {

    public static Allocation convertAllocationProxy(final AllocationInterfacePrx prx) {
        return new Allocation() {
            String _id = prx.ice_getIdentity().name;
            public String getAllocationId() { return _id; }
            public String getId() { return _id; }
            public String getName() { throw new RuntimeException("not implemented"); }
            public String getFacilityId() { throw new RuntimeException("not implemented"); }
        };
    }

    public static List<Allocation> convertAllocationProxyList(List<AllocationInterfacePrx> allocs)  {
        final List<Allocation> result = new ArrayList<Allocation>();
        for (final AllocationInterfacePrx proxy: allocs) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new Allocation() {
                String _id = id;
                public String getAllocationId() { return _id; }
                public String getId() { return _id; }
                public String getName() { throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;
    }

    public static List<Subscription> convertSubscriptionProxyList(List<SubscriptionInterfacePrx> subs)  {
        final List<Subscription> result = new ArrayList<Subscription>();
        for (final SubscriptionInterfacePrx proxy: subs) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new Subscription() {
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

    public static List<Job> convertJobProxyList(List<JobInterfacePrx> jobs) {
        final List<Job> result = new ArrayList<Job>();
        for (final JobInterfacePrx proxy: jobs) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new Job() {
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

    public static List<Group> convertGroupProxyList(List<GroupInterfacePrx> groups) {
        final List<Group> result = new ArrayList<Group>();
        for (final GroupInterfacePrx proxy: groups) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new Group() {
                String _id = id;
                public String getShowId() {  throw new RuntimeException("not implemented"); }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getGroupId() { return _id; }
            });
        }
        return result;
    }

    public static List<Layer> convertLayerProxyList(List<LayerInterfacePrx> layers) {
        final List<Layer> result = new ArrayList<Layer>();
        for (final LayerInterfacePrx proxy: layers) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new Layer() {
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

    public static Group convertGroupProxy(GroupInterfacePrx proxy) {
        final String id = proxy.ice_getIdentity().name;
        return new Group() {
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

    public static List<Host> convertHostProxyList(List<HostInterfacePrx> hosts) {
        final List<Host> result = new ArrayList<Host>(hosts.size());
        for (final HostInterfacePrx proxy: hosts) {
            final String id = proxy.ice_getIdentity().name;
            result.add(new Host() {
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

