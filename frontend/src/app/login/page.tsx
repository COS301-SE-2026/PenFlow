//import Link from "next/link";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  return (
    <main className="auth-page min-h-screen flex flex-col">
      <NavBar />

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="w-full max-w-[420px]">

          <h1 className="auth-title text-center mb-8 text-[3.5rem] leading-none tracking-widest">
            LOGIN
          </h1>

          <div className="auth-card rounded-2xl p-8">
            <Button
              asChild
              className = "auth-btn h-11 w-full rounded-full text-sm font-semibold tracking-widest"
            >
              <a href = "/api/auth/login">
                LOGIN
              </a>
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
