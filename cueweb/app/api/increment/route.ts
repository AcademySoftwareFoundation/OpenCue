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

// Endpoint to increment Prometheus metric - username counter
export async function GET(request: NextRequest) {
  const username = request.nextUrl.searchParams.get("username");

  if (!username) {
      // Return an HTTP 400 response if the username is not provided in the request
      return new NextResponse('Username parameter is missing', { status: 400 });
  }

  const metricsService = MetricsService.getInstance();

  try {
    // Ensure the counter is registered before trying to increment
    metricsService.registerCounter('username_counter', 'Counts how often each user accesses CueWeb');

    // Increment the counter for the provided username
    metricsService.incrementCounter('username_counter', username);

    // Return an HTTP 200 response on successful increment
    return new NextResponse('Metric incremented successfully for user: ' + username, { status: 200 });
  } catch (error) {
    // Log the error and return an HTTP 500 response if an error occurs
    handleError(`Error incrementing metric for username: ${username}\nError: ${error}`)
    return new NextResponse('Error in processing your request', { status: 500 });
  }
}
