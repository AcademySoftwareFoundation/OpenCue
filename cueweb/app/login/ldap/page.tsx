'use client'

// Custom authentication page
import { signIn } from "next-auth/react";
import React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import CueWebIcon from "@/components/ui/cuewebicon";
import { handleError } from "@/app/utils/notify_utils";
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export default function Page() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [password, setPassword] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        let res = null;

    try {
        res = await signIn("credentials", {
            redirect: false,
            name,
            password,
        });
    } catch(error) {
        handleError(error, "An error occured on server side")
        return;
    }

    if (res?.error){
        handleError(res?.error, "Authentication Failed")
        return;
    }

    // Redirect on success
    router.push("/");
    };


    return (
        <div className="flex flex-col sm:flex-row w-full justify-center items-center h-screen bg-gray-100 
            dark:bg-gray-800">
            <ToastContainer />
            <div className="flex flex-col sm:flex-row sm:space-x-20 max-w-[100vh] bg-white dark:bg-black sm:px-16 
                sm:py-8 rounded-xl">
                <div className="flex flex-col justify-center items-center">
                    <CueWebIcon/>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="flex flex-col w-full space-y-3 ">
                        <div className="mb-4">
                            <input type="text" name="name" placeholder="Login" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2 border rounded" required />
                        </div>
                        <div className="mb-4">
                            <input type="password" name="password" placeholder="Passsword" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2 border rounded" required />
                        </div>
                        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition" > Sign In </button>    
                    </div>
                </form>
            </div>
        </div>
        
    );
}
