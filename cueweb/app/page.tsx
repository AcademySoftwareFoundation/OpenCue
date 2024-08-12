import { getJobsForUser } from "@/app/utils/utils";
import { authOptions } from '@/lib/auth';
import { getServerSession } from 'next-auth';
import dynamic from "next/dynamic";
import { redirect } from 'next/navigation';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { columns, Job } from "./jobs/columns";

// Optionally import this config to setup Sentry on the client side
// import '../sentry.client.config';

// Disable server-side rendering of the DataTable component since it requires the browser/window
// to be loaded in order to access localStorage. This fixes 'localStorage not defined' error
const DataTable = dynamic(() => import("@/app/jobs/data-table"), {
  ssr: false,
});

export default async function Page() {
  const session = await getServerSession(authOptions);
  let data: Job[] = [];
  
  if (session && session.user && session.user.email) {
    const username = session.user.email.split('@')[0];
    // Increment Prometheus metric - number of log ins for this user
    try {
      await fetch(`${process.env.NEXTAUTH_URL}/api/increment?username=${username}`);
      // Compile metrics endpoint initially
      await fetch(`${process.env.NEXTAUTH_URL}/api/metrics`);
    } catch (error) {
      console.error("Error incrementing metrics:", error);
      toast.error("Failed to increment user metrics");
    }
    
    try {
      data = await getJobsForUser(username);
    } catch (error) {
      console.error("Error fetching jobs:", error);
      toast.error("Failed to fetch jobs");
    }
  } else {
    redirect('/login');
    return;
  }

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <ToastContainer />
      <DataTable columns={columns} data={data} session={session}/>
    </div>
  );
}
