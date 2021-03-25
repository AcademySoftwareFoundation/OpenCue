
/*
 * Copyright Contributors to the OpenCue Project
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


package com.imageworks.spcue.test.service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.SpecBuilderException;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobSpec;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;


@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class JobSpecTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    JobLauncher jobLauncher;

    private static String readJobSpec(String name)
    {
        String path = "src/test/resources/conf/jobspec/" + name;
        byte[] encoded = null;

        try {
            encoded = Files.readAllBytes(Paths.get(path));
        } catch (IOException e) {
            fail("readJobSpec should succeed to read jobspec file");
        }

        return new String(encoded, StandardCharsets.UTF_8);
    }

    @Test
    public void testParseSuccess() {
        String xml = readJobSpec("jobspec_1_10.xml");
        JobSpec spec = jobLauncher.parse(xml);
        assertEquals(spec.getDoc().getDocType().getPublicID(),
                "SPI Cue Specification Language");
        assertEquals(spec.getDoc().getDocType().getSystemID(),
                "http://localhost:8080/spcue/dtd/cjsl-1.10.dtd");
        assertEquals(spec.getJobs().size(), 1);
        assertEquals(spec.getJobs().get(0).detail.name, "testing-default-testuser_test");
    }

    @Test
    public void testParseNonExistent() {
        String xml = readJobSpec("jobspec_nonexistent_dtd.xml");
        try {
            jobLauncher.parse(xml);
            fail("Expected exception");
        } catch (SpecBuilderException e) {
            assertEquals(e.getMessage(),
                    "Failed to parse job spec XML, java.net.MalformedURLException");
        }
    }

    @Test
    public void testParseInvalidShot() {
        String xml = readJobSpec("jobspec_invalid_shot.xml");
        try {
            jobLauncher.parse(xml);
            fail("Expected exception");
        } catch (SpecBuilderException e) {
            assertEquals(e.getMessage(),
                    "The shot name: invalid/shot is not in the proper format.  " +
                    "Shot names must be alpha numeric, no dashes or punctuation.");
        }
    }

    @Test
    public void testParseGpuSuccess() {
        String xml = readJobSpec("jobspec_1_12.xml");
        JobSpec spec = jobLauncher.parse(xml);
        assertEquals(spec.getDoc().getDocType().getPublicID(),
                "SPI Cue Specification Language");
        assertEquals(spec.getDoc().getDocType().getSystemID(),
                "http://localhost:8080/spcue/dtd/cjsl-1.12.dtd");
        assertEquals(spec.getJobs().size(), 1);
        BuildableJob job = spec.getJobs().get(0);
        assertEquals(job.detail.name, "testing-default-testuser_test");
        LayerDetail layer = job.getBuildableLayers().get(0).layerDetail;
        assertEquals(layer.getMinimumGpus(), 1);
        assertEquals(layer.getMinimumGpuMemory(), 1048576);
    }

}
