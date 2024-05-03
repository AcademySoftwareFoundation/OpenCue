import { NextRequest, NextResponse } from "next/server";
import * as Sentry from "@sentry/nextjs";

export async function POST(request: NextRequest) {
  const body = JSON.stringify(await request.json());
  Sentry.captureMessage(`Request to api/jobs with request body: ${body}`, "info");

  const url = `${process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT}/job.JobInterface/GetJobs`;

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

    // above returns a double nested dictionary with the following structure:
    // {
    //   jobs: {
    //     jobs: [
    //         {Job Object 0}, {Job Object 1}, {Job Object 2},...
    //      ]
    //   }
    // }
    // so we return data.jobs.jobs to return only the array of job objects i.e. [ {Job Object 0}, {Job Object 1}, ...]

    return NextResponse.json({ data: data.jobs.jobs });
  } catch (error) {
    Sentry.captureMessage(`${error}\nRequest body: ${body}`, "error");
    return NextResponse.json({ error: true, errorMessage: error });
  }
}
