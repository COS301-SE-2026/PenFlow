import { NextRequest, NextResponse } from "next/server";
import { registerUser, loginWithPassword } from "@/lib/keycloakService";

const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";

export async function POST(req: NextRequest) {
  const body = await req.json() as Record<string, string>;
  const { username, email, password, firstName, lastName } = body;

  if (!username || !email || !password || !firstName || !lastName) {
    return NextResponse.json(
      { error: "All fields are required" },
      { status: 400 }
    );
  }

  try {
    await registerUser(username, email, password, firstName, lastName);
    const tokens = await loginWithPassword(username, password);

    const res = NextResponse.json({ success: true });

    res.cookies.set("access_token", tokens.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: tokens.expires_in,
      path: "/",
    });

    res.cookies.set("refresh_token", tokens.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: tokens.refresh_expires_in,
      path: "/",
    });

    const provisionRes = await fetch(`${BACKEND_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    }).catch((err: unknown) => {
      console.error("[register] backend unreachable during provisioning:", err);
      return null;
    });

    if (provisionRes && !provisionRes.ok) {
      const body = await provisionRes.text().catch(() => "");
      console.error(`[register] provisioning returned ${provisionRes.status}:`, body);
    }

    return res;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Registration failed";
    const status = message.includes("already exists") ? 409 : 400;
    return NextResponse.json({ error: message }, { status });
  }
}
