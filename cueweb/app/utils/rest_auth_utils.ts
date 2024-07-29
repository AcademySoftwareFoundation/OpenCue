import { loadClientEnvVars, loadServerEnvVars } from "@/app/utils/config";
import jwt from "jsonwebtoken";
import { NextResponse } from "next/server";

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

// Handles the fetching of objects from the gRPC REST gateway including creating authentication tokens
export async function fetchObjectFromRestGateway(endpoint: string, method: string, body: string): Promise<NextResponse> {
  const { NEXT_PUBLIC_OPENCUE_ENDPOINT } = loadClientEnvVars();

  const url = `${NEXT_PUBLIC_OPENCUE_ENDPOINT}${endpoint}`;
  // Parameters for creating the jwt token
  const jwtParams: JwtParams = {
      sub: "user-id", // Replace with a user id
      role: "user-role", // Replace with the user's role
      iat: Math.floor(Date.now() / 1000), // Time the token was issued at
      exp: Math.floor(Date.now() / 1000) + (60 * 60 * 1), // Time the token expires at (1 hour from iat)
  }
  const jwtToken = createJwtToken(jwtParams);

  // Assume a status 400 (bad request) which will be the
  // default value if there is an error thrown while trying to fetch below
  let status = 400;

  // Fetching from the gRPC REST gateway
  try {
      const response = await fetch(url, {
          method: method,
          headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${jwtToken}`,
          },
          body: body,
      });

      const responseBody = await response.text();
      status = response.status;

      // If there are errors returned from the gRPC REST gateway, throw an error
      if (!response.ok) {
          let errorText = responseBody;
          if (response.status === 401) {
              throw new Error(`Unauthorized request: ${errorText}`);
          } else if (response.status === 404) {
              throw new Error(`Resource not found: ${errorText}`);
          } else {
              throw new Error(`Unexpected API Error: ${errorText}`);
          }
      }

      return NextResponse.json({ data: JSON.parse(responseBody) }, { status: status });
  } catch (error) {
      console.error(`Fetch error: ${error}`);
      // Catch any errors either from the gRPC REST gateway or from this function
      // and return them and their status codes
      return NextResponse.json({ error: (error as Error).message }, { status: status });
  }
}

// Create the JWT token given the payload parameters
export function createJwtToken({ sub, role, iat, exp }: JwtParams): string {
  // loading server side environment variables
  const { NEXT_JWT_SECRET } = loadServerEnvVars();
  const payload = {
      sub: sub, // User id
      role: role, // User role
      iat: iat, // Issued at time
      exp: exp, // Expiration time
  };
  
  return jwt.sign(payload, NEXT_JWT_SECRET as string);
}
