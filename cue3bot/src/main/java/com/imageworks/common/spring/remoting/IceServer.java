
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



package com.imageworks.common.spring.remoting;

import java.util.Properties;
import java.util.Map.Entry;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.log4j.Logger;
import Ice.InitializationData;

public class IceServer {

    private static final Logger logger = Logger.getLogger(IceServer.class);

    private static final String DEFAULT_NAME = "SimpleServer";
    private static final int DEFAULT_PORT = 10052;

    private String name;
    private int port;

    private Ice.Communicator communicator;
    private Ice.ObjectAdapter adapter;
    private Thread iceThread;

    private AtomicBoolean isShutdown = new AtomicBoolean(false);

    // Count for requests that return data
    public static final AtomicLong dataRequests = new AtomicLong(0);

    // Count for requests that execute a method without returning a value
    public static final AtomicLong rpcRequests = new AtomicLong(0);

    // Count for errors.
    public static final AtomicLong errors = new AtomicLong(0);

    public IceServer() {
        this(DEFAULT_NAME, DEFAULT_PORT, new Properties());
    }

    public IceServer(String name, int port, Properties props) {
        this.name = name;
        this.port = port;

        InitializationData init_data = new Ice.InitializationData();
        init_data.properties = Ice.Util.createProperties() ;

        for(Entry<Object, Object> set: props.entrySet()) {
            init_data.properties.setProperty((String)set.getKey(), (String) set.getValue());
        }

        communicator = Ice.Util.initialize(new String[] {}, init_data);
    }

    public Ice.ObjectAdapter getAdapter() {
        return this.adapter;
    }

    public Ice.Communicator getCommunicator() {
        return communicator;
    }

    public void start() {
        logger.info("Starting ice server: " + name + " on port " + port);
        adapter =
                communicator.createObjectAdapterWithEndpoints(name,
                        "default -p " + String.valueOf(port));

        iceThread = new IceThread();
        iceThread.start();
    }

    public void shutdown() {
        if (!isShutdown.getAndSet(true)) {
            logger.info("Shutting down ice server: " + name + " on port " + port);
            if (communicator != null) {
                try {
                    communicator.shutdown();
                    communicator.destroy();
                } catch (Exception e) {
                    System.err.println(e.getMessage());
                }
            }
        }
    }

    public class IceThread extends Thread {

        public void run() {
            try {
                communicator.waitForShutdown();
            } catch (Ice.LocalException e) {
                e.printStackTrace();
            } catch (Exception e) {
                System.err.println(e.getMessage());
            }
        }
    }

}

