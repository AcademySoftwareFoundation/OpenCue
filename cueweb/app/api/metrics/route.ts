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
