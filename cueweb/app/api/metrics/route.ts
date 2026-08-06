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

import { NextRequest, NextResponse } from "next/server";
import MetricsService from "@/lib/metrics-service";
import { handleError } from "@/app/utils/notify_utils";

//endpoint to return prometheus metrics
export async function GET(request: NextRequest) {

  const metricsService = MetricsService.getInstance();

  // Return current metrics
  try {
    const metrics = await metricsService.getMetrics();
    return new Response(metrics, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; version=0.0.4'
      }
    });
  } catch (error) {
    handleError(`Failed to retrieve metrics: ${error}`);
    return new Response('Internal server error', { status: 500 });
  }
}
