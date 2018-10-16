
package com.imageworks.common.spring.remoting;

import java.io.IOException;
import java.util.Properties;

import com.imageworks.spcue.servant.ManageAllocation;
import com.imageworks.spcue.servant.ManageFacility;
import io.grpc.Server;
import io.grpc.ServerBuilder;
import org.apache.log4j.Logger;

import com.imageworks.spcue.servant.RqdReportStatic;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;


public class GrpcServer implements ApplicationContextAware {

    private static final Logger logger = Logger.getLogger(GrpcServer.class);

    private static final String DEFAULT_NAME = "CueGrpcServer";
    private static final String DEFAULT_PORT = "8443";

    private String name;
    private int port;
    private Server server;
    private ApplicationContext applicationContext;

    public GrpcServer() {
        this(DEFAULT_NAME, DEFAULT_PORT, new Properties());
    }

    public GrpcServer(String name, String port, Properties props) {
        logger.info("Setting up gRPC server...");
        this.name = name;
        this.port = Integer.parseInt(port);
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
                .addService(new RqdReportStatic())
                .addService(applicationContext.getBean("manageAllocation", ManageAllocation.class))
                .addService(applicationContext.getBean("manageFacility", ManageFacility.class))
                .build();
        server.start();
        logger.info("gRPC server started on " + this.name + " at port " + this.port + " !");
    }

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        this.applicationContext = applicationContext;
    }
}
