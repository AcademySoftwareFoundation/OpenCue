package com.imageworks.spcue.servant;

import com.imageworks.spcue.dispatcher.HostReportHandler;

import com.imageworks.spcue.grpc.report.*;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.annotation.TypeAlias;
import org.springframework.data.redis.connection.jedis.JedisConnectionFactory;
import org.springframework.data.redis.connection.stream.Consumer;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.ReadOffset;
import org.springframework.data.redis.connection.stream.StreamOffset;
import org.springframework.data.redis.stream.StreamListener;
import org.springframework.data.redis.stream.StreamMessageListenerContainer;
import org.springframework.data.redis.stream.Subscription;

import javax.annotation.PostConstruct;
import java.time.Duration;

@TypeAlias("com.imageworks.spcue.servant.RedisConsumer")
public class RedisConsumer {
    private static final Logger logger = Logger.getLogger(RedisConsumer.class);
    //    public Jedis jedis = new Jedis("rhel7testbot-vm.spimageworks.com", 6379);
    @Autowired
    @Qualifier("jedisConnectionFactory")
    private JedisConnectionFactory redisConnectionFactory;
    private HostReportHandler hostReportHandler;
    private StreamListener<String, MapRecord<String, String, String>> streamListener;
    private StreamMessageListenerContainer<String, MapRecord<String, String, String>> listenerContainer;
    private Subscription subscription;

    @PostConstruct
    public void afterPropertiesSet() throws Exception {
        this.streamListener = new RedisStreamListener(hostReportHandler);
        String consumerName = "Cuebot1";
        String consumerGroupName = "test-consumer-group";
        String streamName = "my_stream";

        this.listenerContainer = StreamMessageListenerContainer.create(redisConnectionFactory,
                StreamMessageListenerContainer.StreamMessageListenerContainerOptions.builder()
                        .pollTimeout(Duration.ofMillis(100))
                        .build());

        this.subscription = listenerContainer.receive(
                Consumer.from(consumerGroupName, consumerName),
                StreamOffset.create(streamName, ReadOffset.lastConsumed()),
                streamListener
        );
        subscription.await(Duration.ofSeconds(2));
        listenerContainer.start();
    }

    public void setHostReportHandler(HostReportHandler hostReportHandler) {
        this.hostReportHandler = hostReportHandler;
    }

}