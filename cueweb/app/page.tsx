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

import { getJobsForUser } from "@/app/utils/get_utils";
import { authOptions } from '@/lib/auth';
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { columns, Job } from "./jobs/columns";
import { UNKNOWN_USER } from "@/app/utils/constants";
// Next.js 15 disallows `ssr: false` in `next/dynamic` from Server Components.
// DataTable is loaded client-only because it touches localStorage on mount.
import DataTable from "./jobs/data-table-client";

// Optionally import this config to setup Sentry on the client side
// import '../sentry.client.config';

export default async function Page() {
  const session = await getServerSession(authOptions);
  let username = UNKNOWN_USER;
  
  if (session && session.user) {
    if (session.user.email) {
        username = session.user.email.split('@')[0];
    }
    else if (session.user.name) {
        username = session.user.name;
    }

    // Increment Prometheus metric - number of log ins for this user
    try {
      await fetch(`${process.env.NEXTAUTH_URL}/api/increment?username=${username}`);
      // Compile metrics endpoint initially
      await fetch(`${process.env.NEXTAUTH_URL}/api/metrics`);
    } catch (error) {
      console.error("Error incrementing metrics:", error);
    }
    
  // Ensure that NEXT_PUBLIC_AUTH_PROVIDER is configured as outlined in the cueweb/README.md to correctly set up login authentication
  } else if (process.env.NEXT_PUBLIC_AUTH_PROVIDER) {
    redirect('/login');
    return;
  }

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <ToastContainer />
      <DataTable columns={columns} username={username}/>
    </div>
  );
}
