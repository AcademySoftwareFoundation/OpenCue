
package com.imageworks.spcue.dispatcher;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Map;

import org.junit.Test;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;

/** A batch reads each job's and each layer's environment once, whatever its frame count. */
public class LaunchEnvTests {

    private static DispatchFrame frame(String job, String layer, String id) {
        DispatchFrame f = new DispatchFrame();
        f.jobId = job;
        f.layerId = layer;
        f.id = id;
        return f;
    }

    @Test
    public void oneReadPerJobAndPerLayer() {
        JobDao jobs = mock(JobDao.class);
        LayerDao layers = mock(LayerDao.class);
        when(jobs.getEnvironment(any())).thenReturn(Map.of("JOB", "1"));
        when(layers.getLayerEnvironment(any())).thenReturn(Map.of("LAYER", "1"));
        LaunchEnv env = new LaunchEnv();
        DispatchFrame a1 = frame("job", "layerA", "a1");
        DispatchFrame a2 = frame("job", "layerA", "a2");
        DispatchFrame b1 = frame("job", "layerB", "b1");
        assertSame(env.job(a1, jobs), env.job(a2, jobs));
        assertSame(env.job(a1, jobs), env.job(b1, jobs));
        assertSame(env.layer(a1, layers), env.layer(a2, layers));
        assertEquals(Map.of("LAYER", "1"), env.layer(b1, layers));
        verify(jobs, times(1)).getEnvironment(any());
        verify(layers, times(2)).getLayerEnvironment(any());
    }
}
