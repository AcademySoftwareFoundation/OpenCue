import { fetchObjectFromRestGateway } from '@/app/utils/rest_auth_utils';
import * as Sentry from "@sentry/nextjs";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/app/utils/utils";

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/GetJob";
  const method = request.method;
  const body = JSON.stringify(await request.json());

  Sentry.captureMessage(`Request to api/route with request body: ${body}`, "info");

  // Default status to 500 (Internal Server Error)
  let status = 500;

  try {
    const response = await fetchObjectFromRestGateway(endpoint, method, body);
    const responseData = await response.json();
    status = await response.status;

    if (responseData.error) {
      throw new Error(responseData.error);
    }

    return NextResponse.json({ data: responseData.data.job }, { status: status });
  } catch (error) {
    if (error instanceof Error) {
      handleError(error);
      return NextResponse.json({ error: error.message }, { status: status });
    }
    const unknownError = 'An unknown error occurred';
    handleError(`${unknownError}\nRequest body: ${body}`)
    return NextResponse.json({ error: unknownError }, { status: status });
  }
}
