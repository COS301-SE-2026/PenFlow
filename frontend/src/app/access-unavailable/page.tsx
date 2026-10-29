import Link from "next/link";

export default function AccessUnavailablePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050914] px-6 text-foreground">
      <div className="max-w-md rounded-xl border border-brand-panel-border bg-[#071522] p-8">
        <h1 className="text-3xl">Access unavailable</h1>

        <p className="mt-3 text-muted-foreground">
          We could not verify access to this section. Try again
          later, or contact Service Delivery if this continues.
        </p>

        <div className="mt-6 flex gap-5">
          <Link href="/" className="text-brand-cyan">
            Return home
          </Link>

          <Link href="/api/auth/login" className="text-brand-cyan">
            Sign in again
          </Link>
        </div>
      </div>
    </main>
  );
}