import { NextRequest, NextResponse } from "next/server";
import MetricsService from "@/lib/metrics-service";
import * as Sentry from "@sentry/nextjs";

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
    Sentry.captureMessage(`Failed to retrieve metrics: ${error}`, "error");
    return new Response('Internal server error', { status: 500 });
  }
}