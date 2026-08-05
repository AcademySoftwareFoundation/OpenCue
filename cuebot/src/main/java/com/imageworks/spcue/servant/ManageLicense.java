
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.servant;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.dispatcher.LicenseSource;
import com.imageworks.spcue.grpc.license.License;
import com.imageworks.spcue.grpc.license.LicenseFindRequest;
import com.imageworks.spcue.grpc.license.LicenseFindResponse;
import com.imageworks.spcue.grpc.license.LicenseGetAllRequest;
import com.imageworks.spcue.grpc.license.LicenseGetAllResponse;
import com.imageworks.spcue.grpc.license.LicenseInterfaceGrpc;
import com.imageworks.spcue.grpc.license.LicenseSourceStatus;

/**
 * Read-only view of the live application licenses {@link LicenseSource} polls from
 * {@code scheduler.license.provider}.
 *
 * Unlike the other servants this one reads no database entity: license state deliberately lives
 * in-process (a poll of the license server), so the wire view comes straight from the cached
 * sample. There are no mutations here by design -- the numbers belong to the license server, and
 * the tuning (provider, headroom, poll cadence) is an {@code opencue.properties} concern.
 */
public class ManageLicense extends LicenseInterfaceGrpc.LicenseInterfaceImplBase {

    private LicenseSource licenseSource;

    @Override
    public void getAll(LicenseGetAllRequest request,
            StreamObserver<LicenseGetAllResponse> responseObserver) {
        LicenseSource.SourceStatus status = licenseSource.describe();
        LicenseGetAllResponse.Builder response =
                LicenseGetAllResponse.newBuilder().setSource(toSourceProto(status));
        for (LicenseSource.LicenseInfo info : status.licenses) {
            response.addLicenses(toLicenseProto(info));
        }
        responseObserver.onNext(response.build());
        responseObserver.onCompleted();
    }

    @Override
    public void find(LicenseFindRequest request,
            StreamObserver<LicenseFindResponse> responseObserver) {
        // Names are lowercased everywhere in the licensing path (provider parse,
        // CUE_LICENSES split), so a mixed-case query should still find its pool.
        String name = request.getName().trim().toLowerCase();
        for (LicenseSource.LicenseInfo info : licenseSource.describe().licenses) {
            if (info.state.name.equals(name)) {
                responseObserver.onNext(
                        LicenseFindResponse.newBuilder().setLicense(toLicenseProto(info)).build());
                responseObserver.onCompleted();
                return;
            }
        }
        responseObserver.onError(Status.NOT_FOUND
                .withDescription("No license '" + name + "' in the current provider sample.")
                .asRuntimeException());
    }

    private static License toLicenseProto(LicenseSource.LicenseInfo info) {
        return License.newBuilder().setName(info.state.name).setFeature(info.state.feature)
                .setTotal(info.state.total).setAvailable(info.state.available)
                .setHostBased(info.state.hostBased).setHeadroom(info.headroom)
                .setRunningFrames(info.runningFrames).setRunningHosts(info.runningHosts)
                .setProviderHostCount(info.state.hosts.size()).build();
    }

    private static LicenseSourceStatus toSourceProto(LicenseSource.SourceStatus status) {
        return LicenseSourceStatus.newBuilder().setConfigured(status.configured)
                .setProvider(status.provider).setEnvKey(status.envKey)
                .setPollSeconds(status.pollSeconds).setStaleSeconds(status.staleSeconds)
                .setHasSample(status.hasSample).setAgeSeconds(status.ageSeconds)
                .setStale(status.stale).build();
    }

    public LicenseSource getLicenseSource() {
        return licenseSource;
    }

    public void setLicenseSource(LicenseSource licenseSource) {
        this.licenseSource = licenseSource;
    }
}
