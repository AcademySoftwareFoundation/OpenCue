import { handleRoute } from '@/app/utils/api_utils';
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const endpoint = "/comment.CommentInterface/Save";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  const body = JSON.stringify(await request.json());
  const jsonBody = JSON.parse(body);
  if (
    !jsonBody ||
    typeof jsonBody !== 'object' ||
    !jsonBody.comment ||
    typeof jsonBody.comment.id !== 'string' ||
    !jsonBody.comment.id ||
    typeof jsonBody.comment.subject !== 'string' ||
    !jsonBody.comment.subject
  ) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error, status: response.status });
  return NextResponse.json({ data: responseData.data, status: responseData.status });
}
