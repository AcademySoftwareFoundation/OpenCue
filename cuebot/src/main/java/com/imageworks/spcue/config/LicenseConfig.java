
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

package com.imageworks.spcue.config;

import javax.sql.DataSource;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;

import com.imageworks.spcue.dispatcher.LicenseBookingGate;
import com.imageworks.spcue.dispatcher.LicenseSource;

/**
 * Live application licensing (CUE_LICENSES) beans, shared between the main and test contexts so the
 * XML-defined dispatcher beans can reference them in both. Everything here is inert unless
 * scheduler.license.provider is configured AND a layer declares licenses in its environment.
 */
@Configuration
public class LicenseConfig {

    /**
     * Live view of floating application licenses. The poller is a no-op unless
     * scheduler.license.provider is configured; a layer declaring licenses in its environment is
     * what turns gating on.
     */
    @Bean(initMethod = "start", destroyMethod = "stop")
    public LicenseSource licenseSource(Environment env, DataSource cueDataSource) {
        return new LicenseSource(env, new JdbcTemplate(cueDataSource));
    }

    /** Applies the license budgets to the legacy booking path. */
    @Bean
    public LicenseBookingGate licenseBookingGate(LicenseSource licenseSource,
            DataSource cueDataSource) {
        return new LicenseBookingGate(new JdbcTemplate(cueDataSource), licenseSource);
    }
}
