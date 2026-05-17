import Link from "next/link";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
            <form className="flex flex-col gap-6">

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="login-username"
                  className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                >
                  Username
                </Label>
                <Input
                  id="login-username"
                  name="username"
                  type="text"
                  placeholder="enter username"
                  required
                  className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label
                  htmlFor="login-password"
                  className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                >
                  Password
                </Label>
                <Input
                  id="login-password"
                  name="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                />
              </div>

              <Button
                type="submit"
                className="auth-btn mt-1 h-11 w-full rounded-full text-sm font-semibold tracking-widest cursor-pointer transition-all duration-200 hover:-translate-y-px"
              >
                LOGIN
              </Button>
            </form>
          </div>

          <p className="text-center mt-6 text-sm text-brand-muted">
            No account yet?{" "}
            <Link
              href="/register"
              className="text-brand-cyan font-semibold transition-colors duration-150 hover:underline"
            >
              Register
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
