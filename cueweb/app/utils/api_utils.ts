import jwt from "jsonwebtoken";
import { NextResponse } from "next/server";
import { handleError } from "./notify_utils";

/************************************************************/
// Utility functions for accessing the Api including:
// - helping functions fetch objects from the REST gateway
// - creating jwt tokens used to access the REST gateway
// - accessing action api's which return success or failure
// - accessing get api's which return objects
/************************************************************/

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

// Handles the fetching of objects from the gRPC REST gateway including creating authentication tokens
export async function fetchObjectFromRestGateway(
    endpoint: string,
    method: string,
    body: string
  ): Promise<NextResponse> {
    const NEXT_PUBLIC_OPENCUE_ENDPOINT = process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT;
    const url = `${NEXT_PUBLIC_OPENCUE_ENDPOINT}${endpoint}`;
  
    const jwtParams: JwtParams = {
      sub: "user-id", // Replace with a user id
      role: "user-role", // Replace with the user's role
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
    };
    const jwtToken = createJwtToken(jwtParams);
  
    try {
      const response = await fetch(url, {
        method: method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${jwtToken}`,
        },
        body: body,
      });
  
      const responseBody = await response.text();
      if (!response.ok) {
        handleFetchError(response.status, responseBody);
      }
  
      return NextResponse.json({ data: JSON.parse(responseBody) }, { status: response.status });
    } catch (error) {
      console.error(`Fetch error: ${error}`);
      handleError(error);
      return NextResponse.json({ error: (error as Error).message }, { status: 500 });
    }
  }

// Create the JWT token given the payload parameters
export function createJwtToken({ sub, role, iat, exp }: JwtParams): string {
    const NEXT_JWT_SECRET = process.env.NEXT_JWT_SECRET;
    const payload = { sub, role, iat, exp };
    return jwt.sign(payload, NEXT_JWT_SECRET as string);
  }
  

// Helper function to access a post API with a success or failure returned and handle any errors.
// Actions follow this format: post to the API and see if the action was successful
export async function accessActionApi(endpoint: string, body: string | string[]): Promise<{ success?: boolean; error?: string }> {
    const NEXT_PUBLIC_URL = process.env.NEXT_PUBLIC_URL;
    const bodyAr = Array.isArray(body) ? body : [body];
  
    try {
      // Run all API requests in parallel for better performance
      await Promise.all(
        bodyAr.map(async (curBody) => {
          const response = await fetch(`${NEXT_PUBLIC_URL}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: curBody,
          });
          const res = await response.json();

          if (res.error) {
            throw new Error(res.error);
          }
        })
      );
      return { success: true };
    } catch (error) {
      handleError(error, `Error at ${endpoint}`);
      return { error: (error as Error).message };
    }
  }
  

// Helper function to access object retrieval APIs that return arrays of objects (jobs, layers, or frames).
export async function accessGetApi(endpoint: string, body: string): Promise<any> {
    const NEXT_PUBLIC_URL = process.env.NEXT_PUBLIC_URL;
  
    try {
      const response = await fetch(`${NEXT_PUBLIC_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body,
      });
      const res = await response.json();
  
      if (res.error) {
        throw new Error(res.error);
      }
      return res.data;
    } catch (error) {
      handleError(error, `Error at ${endpoint}`);
      return null;
    }
  }
  

// Centralized route handler to fetch data and handle errors
export async function handleRoute(
    method: string,
    endpoint: string,
    body: string,
    log = false
  ): Promise<NextResponse> {
    try {
      const response = await fetchObjectFromRestGateway(endpoint, method, body);
      const responseData = await response.json();
  
      if (responseData.error) {
        throw new Error(responseData.error);
      }
  
      return NextResponse.json({ data: responseData.data }, { status: response.status });
    } catch (error) {
      handleError(error);
      return NextResponse.json({ error: (error as Error).message }, { status: 500 });
    }
  }

// Helper function to handle errors during fetch requests
function handleFetchError(status: number, errorMessage: string): void {
    switch (status) {
      case 401:
        throw new Error(`Unauthorized request: ${errorMessage}`);
      case 404:
        throw new Error(`Resource not found: ${errorMessage}`);
      default:
        throw new Error(`Unexpected API error: ${errorMessage}`);
    }
  }
  