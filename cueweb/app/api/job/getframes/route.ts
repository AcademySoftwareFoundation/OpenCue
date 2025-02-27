import { handleRoute } from '@/app/utils/api_utils';
import { NextRequest, NextResponse } from "next/server";

// The API endpoint queried returns a double nested dictionary with the following structure:
// {
//   frames: {
//     frames: [
//         {Frame Object 0}, {Frame Object 1}, {Frame Object 2},...
//      ]
//   }
// }
// so we return data.frames.frames to return only the array of frame objects
// i.e. [ {Frame Object 0}, {Frame Object 1}, ...]

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/GetFrames";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  const body = JSON.stringify(await request.json());
  const jsonBody = JSON.parse(body);
  if (!jsonBody || typeof jsonBody !== 'object' || !jsonBody.job || !jsonBody.req) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();
  
  if (!response.ok) return NextResponse.json({ error: responseData.error, status: response.status});
  return NextResponse.json({ data: responseData.data.frames.frames, status: responseData.status});
}
