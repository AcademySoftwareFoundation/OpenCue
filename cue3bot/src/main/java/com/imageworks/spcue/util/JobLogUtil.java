
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



package com.imageworks.spcue.util;

import java.io.File;
import com.imageworks.spcue.JobDetail;

public class JobLogUtil {

    public static boolean createJobLogDirectory(String path) {
        File f = new File(path);
        f.mkdir();
        f.setWritable(true, false);
        return f.isDirectory();
    }

    public static boolean shotLogDirectoryExists(String show, String shot) {
        return new File(String.format("/shots/%s/%s/logs", show, shot)).exists();
    }

    public static boolean jobLogDirectoryExists(JobDetail job) {
        return new File(job.logDir).exists();
    }

    public static String getJobLogPath(JobDetail job) {
        StringBuilder sb = new StringBuilder(512);
        sb.append("/shots/");
        sb.append(job.showName);
        sb.append("/");
        sb.append(job.shot);
        sb.append("/logs/");
        sb.append(job.name);
        sb.append("--");
        sb.append(job.id);
        return sb.toString();
    }
}

