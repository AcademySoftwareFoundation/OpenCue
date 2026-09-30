/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import * as Sentry from "@sentry/nextjs";
import { toast } from "react-toastify";

/*********************************************************/
// Functions to handle notifications like:
// - errors through Sentry and toast notifications
// - success through toast notifications
// - warnings through toast notifications
/*********************************************************/

/**
 * Handles errors by logging them either through Sentry (server-side) 
 * or toast (client-side). Falls back to console.error if toast fails.
 * @param error - The error object or message to handle.
 * @param toastMessage - Optional message for the toast notification.
 */
export function handleError(error: unknown, toastMessage?: string): void {
  // If window is undefined, we are on the server side.
  const isServer = typeof window === "undefined";

  if (isServer && process.env.SENTRY_DSN) {
    // Handle error on the server side using Sentry
    if (typeof error === "string") {
      Sentry.captureMessage(error, "error");
    } else if (error instanceof Error) {
      Sentry.captureMessage(error.message, "error");
    } else {
      Sentry.captureMessage("Unknown error type", "error");
    }
  } else {
    // Handle error on the client side with toast notifications
    try {
      if (toastMessage) {
        toast.error(toastMessage);
      }
    } catch (toastError) {
      console.error("Error showing toast notification: ", toastError);
    }
  }

  // Log the error in the console for both client and server
  console.error(error);
}

/**
 * Displays a success message using toast notifications.
 * Falls back to console.error if toast fails.
 * @param message - The success message to display.
 */
export function toastSuccess(message: string): void {
  try {
    toast.success(message);
  } catch (error) {
    console.error("Error showing toast success message: ", error);
  }
}

/**
 * Displays a warning message using toast notifications.
 * Falls back to console.error if toast fails.
 * @param message - The warning message to display.
 */
export function toastWarning(message: string): void {
  try {
    toast.warn(message);
  } catch (error) {
    console.error("Error showing toast warning message: ", error);
  }
}
