
package com.imageworks.common.spring.remoting;

import java.io.IOException;
import java.util.Properties;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import org.apache.log4j.Logger;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;

import com.imageworks.spcue.servant.CueStatic;
import com.imageworks.spcue.servant.ManageAction;
import com.imageworks.spcue.servant.ManageAllocation;
import com.imageworks.spcue.servant.ManageComment;
import com.imageworks.spcue.servant.ManageDeed;
import com.imageworks.spcue.servant.ManageDepartment;
import com.imageworks.spcue.servant.ManageDepend;
import com.imageworks.spcue.servant.ManageFacility;
import com.imageworks.spcue.servant.ManageFilter;
import com.imageworks.spcue.servant.ManageFrame;
import com.imageworks.spcue.servant.ManageGroup;
import com.imageworks.spcue.servant.ManageHost;
import com.imageworks.spcue.servant.ManageJob;
import com.imageworks.spcue.servant.ManageLayer;
import com.imageworks.spcue.servant.ManageLimit;
import com.imageworks.spcue.servant.ManageMatcher;
import com.imageworks.spcue.servant.ManageOwner;
import com.imageworks.spcue.servant.ManageProc;
import com.imageworks.spcue.servant.ManageRenderPartition;
import com.imageworks.spcue.servant.ManageService;
import com.imageworks.spcue.servant.ManageServiceOverride;
import com.imageworks.spcue.servant.ManageShow;
import com.imageworks.spcue.servant.ManageSubscription;
import com.imageworks.spcue.servant.ManageTask;
import com.imageworks.spcue.servant.RqdReportStatic;


public class GrpcServer implements ApplicationContextAware {

    private static final Logger logger = Logger.getLogger(GrpcServer.class);

    private static final String DEFAULT_NAME = "CueGrpcServer";
    private static final String DEFAULT_PORT = "8443";
    private static final int DEFAULT_MAX_MESSAGE_BYTES = 104857600;

    private String name;
    private int port;
    private int maxMessageBytes;
    private Server server;
    private ApplicationContext applicationContext;

    public GrpcServer() {
        this(DEFAULT_NAME, DEFAULT_PORT, new Properties(), DEFAULT_MAX_MESSAGE_BYTES);
    }

    public GrpcServer(String name, String port, Properties props, Integer maxMessageBytes) {
        logger.info("Setting up gRPC server...");
        this.name = name;
        this.port = Integer.parseInt(port);
        this.maxMessageBytes = maxMessageBytes;
    }

    public void shutdown() {
        if (!server.isShutdown()) {
            logger.info("gRPC server shutting down on " + this.name + " at port " + this.port);
            server.shutdown();
        }
    }

    public void start() throws IOException {
        server = ServerBuilder
                .forPort(this.port)
                .addService(applicationContext.getBean("rqdReportStatic", RqdReportStatic.class))
                .addService(applicationContext.getBean("cueStaticServant", CueStatic.class))
                .addService(applicationContext.getBean("manageAction", ManageAction.class))
                .addService(applicationContext.getBean("manageAllocation", ManageAllocation.class))
                .addService(applicationContext.getBean("manageComment", ManageComment.class))
                .addService(applicationContext.getBean("manageDeed", ManageDeed.class))
                .addService(applicationContext.getBean("manageDepartment", ManageDepartment.class))
                .addService(applicationContext.getBean("manageDepend", ManageDepend.class))
                .addService(applicationContext.getBean("manageFacility", ManageFacility.class))
                .addService(applicationContext.getBean("manageFilter", ManageFilter.class))
                .addService(applicationContext.getBean("manageFrame", ManageFrame.class))
                .addService(applicationContext.getBean("manageGroup", ManageGroup.class))
                .addService(applicationContext.getBean("manageHost", ManageHost.class))
                .addService(applicationContext.getBean("manageJob", ManageJob.class))
                .addService(applicationContext.getBean("manageLayer", ManageLayer.class))
                .addService(applicationContext.getBean("manageLimit", ManageLimit.class))
                .addService(applicationContext.getBean("manageMatcher", ManageMatcher.class))
                .addService(applicationContext.getBean("manageOwner", ManageOwner.class))
                .addService(applicationContext.getBean("manageProc", ManageProc.class))
                .addService(applicationContext.getBean("manageRenderPartition", ManageRenderPartition.class))
                .addService(applicationContext.getBean("manageService", ManageService.class))
                .addService(applicationContext.getBean("manageServiceOverride", ManageServiceOverride.class))
                .addService(applicationContext.getBean("manageShow", ManageShow.class))
                .addService(applicationContext.getBean("manageSubscription", ManageSubscription.class))
                .addService(applicationContext.getBean("manageTask", ManageTask.class))
                .maxInboundMessageSize(maxMessageBytes)
                .intercept(new CueServerInterceptor())
                .build();
        server.start();
        logger.info("gRPC server started on " + this.name + " at port " + this.port + " !");
    }

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        this.applicationContext = applicationContext;
    }
}
