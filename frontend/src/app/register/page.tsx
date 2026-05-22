"use client";

import { useState } from "react";
import Link from "next/link";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RegisterPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const form = e.currentTarget;
    const username = (form.elements.namedItem("username") as HTMLInputElement).value;
    const firstName = (form.elements.namedItem("firstName") as HTMLInputElement).value;
    const lastName = (form.elements.namedItem("lastName") as HTMLInputElement).value;
    const email = (form.elements.namedItem("email") as HTMLInputElement).value;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;
    const repeatPassword = (form.elements.namedItem("repeatPassword") as HTMLInputElement).value;

    if (password !== repeatPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, firstName, lastName, email, password }),
      });

      const data = await res.json() as { error?: string };

      if (!res.ok) {
        setError(data.error ?? "Registration failed");
        return;
      }

      setRegistered(true);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (registered) {
    return (
      <main className="auth-page min-h-screen flex flex-col">
        <NavBar />
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
          <div className="w-full max-w-[420px] text-center">
            <h1 className="auth-title text-center mb-8 text-[3rem] leading-none tracking-widest">
              SUCCESS
            </h1>
            <div className="auth-card rounded-2xl p-8 flex flex-col gap-6">
              <p className="text-brand-cyan text-sm">
                Your account has been created successfully.
              </p>
              <Link
                href="/login"
                className="auth-btn h-11 w-full rounded-full text-sm font-semibold tracking-widest flex items-center justify-center transition-all duration-200 hover:-translate-y-px"
              >
                GO TO LOGIN
              </Link>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="auth-page min-h-screen flex flex-col">
      <NavBar />

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-14">
        <div className="w-full max-w-[420px]">

          <h1 className="auth-title text-center mb-8 text-[3rem] leading-none tracking-widest">
            REGISTER
          </h1>

          <div className="auth-card rounded-2xl p-8">
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">

              {error && (
                <p className="text-red-400 text-sm text-center">{error}</p>
              )}

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

              <div className="flex gap-3">
                <div className="flex flex-col gap-2 flex-1">
                  <Label
                    htmlFor="signup-first-name"
                    className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                  >
                    First Name
                  </Label>
                  <Input
                    id="signup-first-name"
                    name="firstName"
                    type="text"
                    placeholder="First"
                    required
                    className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                  />
                </div>
                <div className="flex flex-col gap-2 flex-1">
                  <Label
                    htmlFor="signup-last-name"
                    className="auth-label text-xs font-semibold tracking-[0.12em] uppercase"
                  >
                    Last Name
                  </Label>
                  <Input
                    id="signup-last-name"
                    name="lastName"
                    type="text"
                    placeholder="Last"
                    required
                    className="auth-input h-11 rounded-lg px-4 text-sm placeholder:opacity-40 focus-visible:ring-1"
                  />
                </div>
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
                disabled={loading}
                className="auth-btn mt-2 h-11 w-full rounded-full text-sm font-semibold tracking-widest cursor-pointer transition-all duration-200 hover:-translate-y-px"
              >
                {loading ? "CREATING..." : "CREATE ACCOUNT"}
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
