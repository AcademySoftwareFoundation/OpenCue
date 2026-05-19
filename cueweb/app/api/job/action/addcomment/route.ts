import { handleRoute } from '@/app/utils/api_utils';
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/AddComment";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 });
  }

  if (
    !jsonBody ||
    typeof jsonBody !== 'object' ||
    !jsonBody.job ||
    !jsonBody.new_comment ||
    typeof jsonBody.new_comment.subject !== 'string' ||
    !jsonBody.new_comment.subject
  ) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);

  let responseData: any;
  try {
    responseData = await response.json();
  } catch {
    return NextResponse.json({ error: 'Invalid upstream response' }, { status: 502 });
  }

  if (!response.ok) {
    return NextResponse.json({ error: responseData?.error ?? 'Upstream error' }, { status: response.status });
  }
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
