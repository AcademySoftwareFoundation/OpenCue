
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

package com.imageworks.spcue.util;

import com.imageworks.spcue.JobDetail;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.io.File;

@Component
public class JobLogUtil {

    @Autowired
    private Environment env;

    public boolean createJobLogDirectory(String path) {
        File f = new File(path);
        f.mkdir();
        f.setWritable(true, false);
        return f.isDirectory();
    }

    public String getJobLogDir(String show, String shot, String os) {
        StringBuilder sb = new StringBuilder(512);
        sb.append(getJobLogRootDir(os));
        sb.append("/");
        sb.append(show);
        sb.append("/");
        sb.append(shot);
        sb.append("/logs");
        return sb.toString();
    }

    public String getJobLogPath(JobDetail job) {
        StringBuilder sb = new StringBuilder(512);
        sb.append(getJobLogDir(job.showName, job.shot, job.os));
        sb.append("/");
        sb.append(job.name);
        sb.append("--");
        sb.append(job.id);
        return sb.toString();
    }

    public String getJobLogRootDir(String os) {
        try {
            return env.getRequiredProperty(String.format("log.frame-log-root.%s", os),
                    String.class);
        } catch (IllegalStateException e) {
            return env.getRequiredProperty("log.frame-log-root.default_os", String.class);
        }
    }

    public String getLokiURL() {
        return env.getRequiredProperty("log.loki.url", String.class);
    }
}
