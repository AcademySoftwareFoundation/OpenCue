
package com.imageworks.spcue.servant;


import com.google.protobuf.InvalidProtocolBufferException;
import com.google.protobuf.util.JsonFormat;
import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.grpc.report.HostReport;
import org.apache.log4j.Logger;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.stream.StreamListener;

public class RedisStreamListener implements StreamListener<String, MapRecord<String, String, String>> {
    private static final Logger logger = Logger.getLogger(RedisStreamListener.class);
    private HostReportHandler hostReportHandler;

    public RedisStreamListener(HostReportHandler hostReportHandler) {
        super();
        this.hostReportHandler = hostReportHandler;
    }

    @Override
    public void onMessage(MapRecord<String, String, String> message) {
        long reportTime = System.currentTimeMillis();
        String hostReportData = message.getValue().get("host");
        HostReport.Builder builder = HostReport.newBuilder();
        try {
            JsonFormat.parser().ignoringUnknownFields().merge(hostReportData, builder);
        } catch (InvalidProtocolBufferException e) {
            e.printStackTrace();
        }
        HostReport hostReport = builder.build();
        logger.info("Received Host Report");
        hostReportHandler.handleHostReport(hostReport, false, reportTime);

    }

}