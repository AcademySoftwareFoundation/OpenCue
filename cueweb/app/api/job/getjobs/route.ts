import { handleRoute } from '@/app/utils/api_utils';
import { NextRequest, NextResponse } from "next/server";

// The API endpoint queried returns a double nested dictionary with the following structure:
// {
//   jobs: {
//     jobs: [
//         {Job Object 0}, {Job Object 1}, {Job Object 2},...
//      ]
//   }
// }
// so we return data.jobs.jobs to return only the array of job objects i.e. [ {Job Object 0}, {Job Object 1}, ...]

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/GetJobs";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  const body = JSON.stringify(await request.json());
  const jsonBody = JSON.parse(body);
  if (!jsonBody || typeof jsonBody !== 'object' || !jsonBody.r) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();
  
  if (!response.ok) return NextResponse.json({ error: responseData.error, status: response.status});
  return NextResponse.json({ data: responseData.data.jobs.jobs, status: responseData.status});
}
