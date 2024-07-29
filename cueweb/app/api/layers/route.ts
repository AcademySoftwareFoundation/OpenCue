import { fetchObjectFromRestGateway } from '@/app/utils/rest_auth_utils';
import * as Sentry from "@sentry/nextjs";
import { NextRequest, NextResponse } from "next/server";
import { handleError } from "@/app/utils/utils";

// The API endpoint queried returns a double nested dictionary with the following structure:
// {
//   layers: {
//     layers: [
//         {Layer Object 0}, {Layer Object 1}, {Layer Object 2},...
//      ]
//   }
// }
// so we return data.layers.layers to return only the array of layer objects
// i.e. [ {Layer Object 0}, {Layer Object 1}, ...]

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/GetLayers";
  const method = request.method;
  const body = JSON.stringify(await request.json());

  Sentry.captureMessage(`Request to api/layers with request body: ${body}`, "info");

  // Default status to 500 (Internal Server Error)
  let status = 500;

  try {
    const response = await fetchObjectFromRestGateway(endpoint, method, body);
    const responseData = await response.json();
    status = await response.status;

    if (responseData.error) {
      throw new Error(responseData.error);
    }

    return NextResponse.json({ data: responseData.data.layers.layers }, { status: status });
  } catch (error) {
    if (error instanceof Error) {
      handleError(error);
      return NextResponse.json({ error: error.message }, { status: status });
    }
    const unknownError = `An unknown error occurred\nRequest body: ${body}`;
    handleError(unknownError)
    return NextResponse.json({ error: unknownError }, { status: status });
  }
}
