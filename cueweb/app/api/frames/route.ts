import { NextRequest, NextResponse } from "next/server";
import * as Sentry from "@sentry/nextjs";

export async function POST(request: NextRequest) {
  const body = JSON.stringify(await request.json());
  Sentry.captureMessage(`Request to api/frames with request body: ${body}`, "info");

  const url = `${process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT}/job.JobInterface/GetFrames`;

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
    //   frames: {
    //     frames: [
    //         {Frame Object 0}, {Frame Object 1}, {Frame Object 2},...
    //      ]
    //   }
    // }
    // so we return data.frames.frames to return only the array of frame objects
    // i.e. [ {Frame Object 0}, {Frame Object 1}, ...]

    return NextResponse.json({ data: data.frames.frames });
  } catch (error) {
    Sentry.captureMessage(`${error}\nRequest body: ${body}`, "error");
    return NextResponse.json({ error: true, errorMessage: error });
  }
}
