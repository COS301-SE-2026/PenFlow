import Link from "next/link";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RegisterPage() {
  return (
    <main className="auth-page min-h-screen flex flex-col">
      <NavBar />

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-14">
        <div className="w-full max-w-[420px]">

          <h1 className="auth-title text-center mb-8 text-[3rem] leading-none tracking-widest">
            REGISTER
          </h1>

          <div className="auth-card rounded-2xl p-8">
            <form className="flex flex-col gap-5">

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="signup-username"
                  className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                >
                  Username
                </Label>
                <Input
                  id="signup-username"
                  name="username"
                  type="text"
                  placeholder="choose a username"
                  required
                  className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="signup-email"
                  className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                >
                  Email
                </Label>
                <Input
                  id="signup-email"
                  name="email"
                  type="email"
                  placeholder="you@domain.com"
                  required
                  className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="signup-password"
                  className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                >
                  Password
                </Label>
                <Input
                  id="signup-password"
                  name="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="signup-repeat-password"
                  className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                >
                  Confirm Password
                </Label>
                <Input
                  id="signup-repeat-password"
                  name="repeatPassword"
                  type="password"
                  placeholder="••••••••"
                  required
                  className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                />
              </div>

              <Button
                type="submit"
                className="auth-btn mt-2 h-11 w-full rounded-full text-sm font-semibold tracking-widest cursor-pointer transition-all duration-200 hover:-translate-y-px"
              >
                CREATE ACCOUNT
              </Button>
            </form>
          </div>

          <p className="text-center mt-6 text-sm text-brand-muted">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-brand-cyan font-semibold transition-colors duration-150 hover:underline"
            >
              Login
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
