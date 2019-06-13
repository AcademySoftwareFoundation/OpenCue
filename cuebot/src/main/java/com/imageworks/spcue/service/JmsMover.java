
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



package com.imageworks.spcue.service;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import javax.jms.Message;
import javax.jms.Session;
import javax.jms.Topic;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jms.JmsException;
import org.springframework.jms.core.JmsTemplate;
import org.springframework.jms.core.MessageCreator;

import com.imageworks.spcue.util.CueExceptionUtil;
import org.springframework.stereotype.Component;

@Component
public class JmsMover extends ThreadPoolExecutor {
    private static final Logger logger = Logger.getLogger(JmsMover.class);
    private final Gson gson = new GsonBuilder().serializeNulls().create();

    @Autowired
    private Environment env;

    @Autowired
    private JmsTemplate template;
    private Topic topic;

    private static final int THREAD_POOL_SIZE_INITIAL = 1;
    private static final int THREAD_POOL_SIZE_MAX = 1;
    private static final int QUEUE_SIZE_INITIAL = 1000;

    public JmsMover() {
        super(THREAD_POOL_SIZE_INITIAL, THREAD_POOL_SIZE_MAX, 10 , TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(QUEUE_SIZE_INITIAL));
    }

    public void send(Object m) {
        if (env.getRequiredProperty("messaging.enabled", Boolean.class)) {
            try {
                execute(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            template.send(topic, new MessageCreator() {
                                @Override
                                public Message createMessage(Session session)
                                    throws javax.jms.JMSException {
                                    return session.createTextMessage(gson.toJson(m));
                                }
                            });
                        } catch (JmsException e) {
                            logger.warn("Failed to send JMS message");
                            CueExceptionUtil.logStackTrace(
                                "JmsProducer " + this.getClass().toString() +
                                    " caught error ", e);
                        }
                    }
                });
            } catch (RejectedExecutionException e) {
                logger.warn("Outgoing JMS message queue is full!");
                CueExceptionUtil.logStackTrace(
                    "JmsProducer " + this.getClass().toString() +
                        " caught error ", e);
            }
        }
    }

    public JmsTemplate getTemplate() {
        return template;
    }

    public void setTemplate(JmsTemplate template) {
        this.template = template;
    }

    public Topic getTopic() {
        return topic;
    }

    public void setTopic(Topic topic) {
        this.topic = topic;
    }
}

