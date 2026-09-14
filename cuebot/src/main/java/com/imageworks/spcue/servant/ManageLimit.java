package com.imageworks.spcue.servant;

import java.util.EnumSet;
import java.util.Set;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.LimitExitStatusClaimedException;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitClearBindingsRequest;
import com.imageworks.spcue.grpc.limit.LimitClearBindingsResponse;
import com.imageworks.spcue.grpc.limit.LimitCreateRequest;
import com.imageworks.spcue.grpc.limit.LimitCreateResponse;
import com.imageworks.spcue.grpc.limit.LimitDeleteRequest;
import com.imageworks.spcue.grpc.limit.LimitDeleteResponse;
import com.imageworks.spcue.grpc.limit.LimitFindRequest;
import com.imageworks.spcue.grpc.limit.LimitFindResponse;
import com.imageworks.spcue.grpc.limit.LimitGetBindingsRequest;
import com.imageworks.spcue.grpc.limit.LimitGetBindingsResponse;
import com.imageworks.spcue.grpc.limit.LimitGetHoldsRequest;
import com.imageworks.spcue.grpc.limit.LimitGetHoldsResponse;
import com.imageworks.spcue.grpc.limit.LimitGetRequest;
import com.imageworks.spcue.grpc.limit.LimitGetResponse;
import com.imageworks.spcue.grpc.limit.LimitGetAllRequest;
import com.imageworks.spcue.grpc.limit.LimitGetAllResponse;
import com.imageworks.spcue.grpc.limit.LimitInterfaceGrpc;
import com.imageworks.spcue.grpc.limit.LimitRenameRequest;
import com.imageworks.spcue.grpc.limit.LimitRenameResponse;
import com.imageworks.spcue.grpc.limit.LimitReportUsageRequest;
import com.imageworks.spcue.grpc.limit.LimitReportUsageResponse;
import com.imageworks.spcue.grpc.limit.LimitSetEnforcementRequest;
import com.imageworks.spcue.grpc.limit.LimitSetEnforcementResponse;
import com.imageworks.spcue.grpc.limit.LimitSetFailureRuleRequest;
import com.imageworks.spcue.grpc.limit.LimitSetFailureRuleResponse;
import com.imageworks.spcue.grpc.limit.LimitSetMaxValueRequest;
import com.imageworks.spcue.grpc.limit.LimitSetMaxValueResponse;
import com.imageworks.spcue.grpc.limit.LimitSetReportTtlRequest;
import com.imageworks.spcue.grpc.limit.LimitSetReportTtlResponse;
import com.imageworks.spcue.grpc.limit.LimitSetSoftValueRequest;
import com.imageworks.spcue.grpc.limit.LimitSetSoftValueResponse;
import com.imageworks.spcue.grpc.limit.LimitSetTypeRequest;
import com.imageworks.spcue.grpc.limit.LimitSetTypeResponse;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageLimit extends LimitInterfaceGrpc.LimitInterfaceImplBase {
    private AdminManager adminManager;
    private Whiteboard whiteboard;

    @Override
    public void create(LimitCreateRequest request,
            StreamObserver<LimitCreateResponse> responseObserver) {
        try {
            String limitId = adminManager.createLimit(request.getName(), request.getMaxValue(),
                    request.getType(), request.getEnforcement(),
                    request.getSoftValue() <= 0 ? -1 : request.getSoftValue(),
                    request.getExitStatus() == 0 ? null : request.getExitStatus(),
                    request.getDelayMinutes(), request.getAutoTag());
            LimitCreateResponse response =
                    LimitCreateResponse.newBuilder().setLimit(whiteboard.getLimit(limitId)).build();
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void delete(LimitDeleteRequest request,
            StreamObserver<LimitDeleteResponse> responseObserver) {
        adminManager.deleteLimit(adminManager.findLimit(request.getName()));
        responseObserver.onNext(LimitDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void find(LimitFindRequest request, StreamObserver<LimitFindResponse> responseObserver) {
        LimitFindResponse response = LimitFindResponse.newBuilder()
                .setLimit(whiteboard.findLimit(request.getName())).build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void get(LimitGetRequest request, StreamObserver<LimitGetResponse> responseObserver) {
        LimitGetResponse response = LimitGetResponse.newBuilder()
                .setLimit(whiteboard.getLimit(request.getId())).build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getAll(LimitGetAllRequest request,
            StreamObserver<LimitGetAllResponse> responseObserver) {
        responseObserver.onNext(
                LimitGetAllResponse.newBuilder().addAllLimits(whiteboard.getLimits()).build());
        responseObserver.onCompleted();
    }

    @Override
    public void rename(LimitRenameRequest request,
            StreamObserver<LimitRenameResponse> responseObserver) {
        adminManager.setLimitName(adminManager.findLimit(request.getOldName()),
                request.getNewName());
        responseObserver.onNext(LimitRenameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxValue(LimitSetMaxValueRequest request,
            StreamObserver<LimitSetMaxValueResponse> responseObserver) {
        adminManager.setLimitMaxValue(adminManager.findLimit(request.getName()),
                request.getMaxValue());
        responseObserver.onNext(LimitSetMaxValueResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setType(LimitSetTypeRequest request,
            StreamObserver<LimitSetTypeResponse> responseObserver) {
        try {
            adminManager.setLimitType(adminManager.findLimit(request.getName()), request.getType());
            responseObserver.onNext(LimitSetTypeResponse.newBuilder().build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void setEnforcement(LimitSetEnforcementRequest request,
            StreamObserver<LimitSetEnforcementResponse> responseObserver) {
        try {
            adminManager.setLimitEnforcement(adminManager.findLimit(request.getName()),
                    request.getEnforcement());
            responseObserver.onNext(LimitSetEnforcementResponse.newBuilder().build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void setSoftValue(LimitSetSoftValueRequest request,
            StreamObserver<LimitSetSoftValueResponse> responseObserver) {
        try {
            adminManager.setLimitSoftValue(adminManager.findLimit(request.getName()),
                    request.getSoftValue());
            responseObserver.onNext(LimitSetSoftValueResponse.newBuilder().build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void setReportTtl(LimitSetReportTtlRequest request,
            StreamObserver<LimitSetReportTtlResponse> responseObserver) {
        try {
            adminManager.setLimitReportTtl(adminManager.findLimit(request.getName()),
                    request.getReportTtl());
            responseObserver.onNext(LimitSetReportTtlResponse.newBuilder().build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void setFailureRule(LimitSetFailureRuleRequest request,
            StreamObserver<LimitSetFailureRuleResponse> responseObserver) {
        try {
            adminManager.setLimitFailureRule(adminManager.findLimit(request.getName()),
                    request.getExitStatus(), request.getDelayMinutes(), request.getAutoTag());
            responseObserver.onNext(LimitSetFailureRuleResponse.newBuilder().build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void getBindings(LimitGetBindingsRequest request,
            StreamObserver<LimitGetBindingsResponse> responseObserver) {
        try {
            Set<LimitBindSource> sources = toSourceSet(request.getSourcesList());
            LimitInterface limit = adminManager.findLimit(request.getLimitName());
            responseObserver.onNext(LimitGetBindingsResponse.newBuilder().addAllBindings(
                    adminManager.getLimitBindings(limit, sources, request.getLayerIdsList()))
                    .build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void clearBindings(LimitClearBindingsRequest request,
            StreamObserver<LimitClearBindingsResponse> responseObserver) {
        try {
            Set<LimitBindSource> sources = toSourceSet(request.getSourcesList());
            LimitInterface limit = adminManager.findLimit(request.getLimitName());
            int removed = adminManager.clearLimitBindings(limit, sources);
            responseObserver
                    .onNext(LimitClearBindingsResponse.newBuilder().setRemoved(removed).build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void reportUsage(LimitReportUsageRequest request,
            StreamObserver<LimitReportUsageResponse> responseObserver) {
        try {
            AdminManager.LimitReportResult result =
                    adminManager.reportLimitUsage(request.getReportsList(), request.getSource());
            LimitReportUsageResponse.Builder response = LimitReportUsageResponse.newBuilder();
            for (String limitId : result.appliedLimitIds) {
                response.addLimits(whiteboard.getLimit(limitId));
            }
            response.addAllUnknownLimits(result.unknownLimits);
            response.addAllSkippedLimits(result.skippedLimits);
            responseObserver.onNext(response.build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    @Override
    public void getHolds(LimitGetHoldsRequest request,
            StreamObserver<LimitGetHoldsResponse> responseObserver) {
        try {
            LimitInterface limit = request.getLimitName().isEmpty() ? null
                    : adminManager.findLimit(request.getLimitName());
            responseObserver.onNext(LimitGetHoldsResponse.newBuilder()
                    .addAllHolds(adminManager.getLimitHolds(limit, request.getHostName())).build());
            responseObserver.onCompleted();
        } catch (RuntimeException e) {
            responseObserver.onError(mapError(e));
        }
    }

    private static Set<LimitBindSource> toSourceSet(Iterable<LimitBindSource> sources) {
        Set<LimitBindSource> set = EnumSet.noneOf(LimitBindSource.class);
        for (LimitBindSource source : sources) {
            if (source == LimitBindSource.UNRECOGNIZED) {
                throw new IllegalArgumentException("Unrecognized binding source.");
            }
            set.add(source);
        }
        return set;
    }

    private static Throwable mapError(RuntimeException e) {
        if (e instanceof EmptyResultDataAccessException) {
            return Status.NOT_FOUND.withDescription("Limit not found.").withCause(e)
                    .asRuntimeException();
        }
        if (e instanceof IllegalArgumentException) {
            return Status.INVALID_ARGUMENT.withDescription(e.getMessage()).withCause(e)
                    .asRuntimeException();
        }
        if (e instanceof LimitExitStatusClaimedException) {
            return Status.ALREADY_EXISTS.withDescription(e.getMessage()).withCause(e)
                    .asRuntimeException();
        }
        return Status.INTERNAL.withDescription(e.getMessage()).withCause(e).asRuntimeException();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }
}
