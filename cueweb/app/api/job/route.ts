import { NextRequest, NextResponse } from "next/server";
import * as Sentry from "@sentry/nextjs";

//endpoint to get a job given its unique id
export async function POST(request: NextRequest) {
  const body = JSON.stringify(await request.json());
  Sentry.captureMessage(`Request to api/job with request body: ${body}`, "info");

  const url = `${process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT}/job.JobInterface/GetJob`;

  try {
    const apiResponse = await fetch(url, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        // Add any other headers required by the external API
      },
      body: body,
    });

    const data = await apiResponse.json();

    return NextResponse.json({ data: data.job });
  } catch (error) {
    Sentry.captureMessage(`${error}\nRequest body: ${body}`, "error");
    return NextResponse.json({ error: true, errorMessage: error });
  }
}
