import { getJobsForUser } from "@/app/utils/get_utils";
import { authOptions } from '@/lib/auth';
import { getServerSession } from 'next-auth';
import dynamic from "next/dynamic";
import { redirect } from 'next/navigation';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { columns, Job } from "./jobs/columns";
import { UNKNOWN_USER } from "@/app/utils/constants";

// Optionally import this config to setup Sentry on the client side
// import '../sentry.client.config';

// Disable server-side rendering of the DataTable component since it requires the browser/window
// to be loaded in order to access localStorage. This fixes 'localStorage not defined' error
const DataTable = dynamic(() => import("@/app/jobs/data-table"), {
  ssr: false,
});

export default async function Page() {
  const session = await getServerSession(authOptions);
  let username = UNKNOWN_USER;
  
  if (session && session.user && session.user.email) {
    username = session.user.email.split('@')[0];
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
