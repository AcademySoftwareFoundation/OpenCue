import { Job, columns } from "./jobs/columns"
import {getServerSession} from 'next-auth'
import {authOptions} from '@/lib/auth'
import {redirect} from 'next/navigation'
import dynamic from "next/dynamic";
import * as Sentry from "@sentry/nextjs";

// https://nextjs.org/docs/pages/building-your-application/optimizing/lazy-loading#with-no-ssr
// disable server-side rendering of the DataTable component since it requires the browser/window (only on client side)
// to be loaded in order to access localStorage. This fixes 'localStorage not defined' error
const DataTable = dynamic(() => import("@/app/jobs/data-table"), {
  ssr: false,
});

async function getJobs(username: string): Promise<Job[]> {

  if (!process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT) {

    Sentry.captureMessage(`environment variable NEXT_PUBLIC_OPENCUE_ENDPOINT not provided`, "log");

    return []
  }

  const url = `${process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT}/job.JobInterface/GetJobs`

  // Fetch data from your API here.
  const res = await fetch(
    url,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    body: `{"r": {"include_finished":false, "users":["${username}"]}}`
  });
  
  if (!res.ok) {
    return [];
  }

  const data = await res.json();

  // the above returns a nested dictionary that has the following structure:
  // {
  //   jobs: {
  //     jobs: [
  //         {Job Object 0}, {Job Object 1}, {Job Object 2},...
  //      ]
  //   }
  // }

  // Since we just want to return the array of job objects, we return data.jobs.jobs:

  return data.jobs.jobs;
}

export default async function Page() {
  const session = await getServerSession(authOptions)
  let data: Job[] = [];
  if (session && session.user && session.user.email) {
    const username = session.user.email.split('@')[0]
    // increment prometheus metric - number of log ins for this user
    try {
      await fetch(`${process.env.NEXTAUTH_URL}/api/increment?username=${username}`);
      // need to compile metrics endpoint initially
      await fetch(`${process.env.NEXTAUTH_URL}/api/metrics`);
    } catch (error){
      console.log(error)
    }
    data = await getJobs(username)
    
  } else {
    redirect('/login');
    return;
  }
  
  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <DataTable columns={columns} data={data} session={session}/>
    </div>
  );
}
