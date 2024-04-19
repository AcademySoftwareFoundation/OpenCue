import { NextRequest, NextResponse } from "next/server";
import * as Sentry from "@sentry/nextjs";

export async function POST(request: NextRequest) {
  const body = JSON.stringify(await request.json());
  Sentry.captureMessage(`Request to api/layers with request body: ${body}`, "info");

  const url = `${process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT}/job.JobInterface/GetLayers`;

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
    //   layers: {
    //     layers: [
    //         {Layer Object 0}, {Layer Object 1}, {Layer Object 2},...
    //      ]
    //   }
    // }
    // so we return data.layers.layers to return only the array of layer objects
    // i.e. [ {Layer Object 0}, {Layer Object 1}, ...]

    return NextResponse.json({ data: data.layers.layers });
  } catch (error) {
    Sentry.captureMessage(`${error}\nRequest body: ${body}`, "error");
    return NextResponse.json({ error: true, errorMessage: error });
  }
}
