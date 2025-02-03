package com.imageworks.common.spring.remoting;

import io.grpc.ForwardingServerCallListener.SimpleForwardingServerCallListener;
import io.grpc.Grpc;
import io.grpc.Metadata;
import io.grpc.ServerCall;
import io.grpc.ServerCallHandler;
import io.grpc.ServerInterceptor;
import io.grpc.Status;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class CueServerInterceptor implements ServerInterceptor {

    private static final Logger logger = LogManager.getLogger(CueServerInterceptor.class);
    private static final Logger accessLogger = LogManager.getLogger("API");

    @Override
    public <ReqT, RespT> ServerCall.Listener<ReqT> interceptCall(ServerCall<ReqT, RespT> serverCall,
            Metadata metadata, ServerCallHandler<ReqT, RespT> serverCallHandler) {
        accessLogger.info("gRPC [" + serverCall.getAttributes().get(Grpc.TRANSPORT_ATTR_REMOTE_ADDR)
                + "]: " + serverCall.getMethodDescriptor().getFullMethodName());

        ServerCall.Listener<ReqT> delegate = serverCallHandler.startCall(serverCall, metadata);
        return new SimpleForwardingServerCallListener<ReqT>(delegate) {
            @Override
            public void onHalfClose() {
                try {
                    super.onHalfClose();
                } catch (Exception e) {
                    logger.error("Caught an unexpected error.", e);
                    serverCall.close(Status.INTERNAL.withCause(e)
                            .withDescription(e.toString() + "\n" + e.getMessage()), new Metadata());
                }
            }

            @Override
            public void onMessage(ReqT request) {
                accessLogger.info("Request Data: " + request);
                super.onMessage(request);
            }
        };
    }
}
