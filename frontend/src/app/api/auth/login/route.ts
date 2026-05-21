import { NextRequest, NextResponse } from "next/server";
import { loginWithPassword } from "@/lib/keycloakService";

const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";

export async function POST(req: NextRequest) {
  const body = await req.json() as Record<string, string>;
  const { username, password } = body;

  if (!username || !password) {
    return NextResponse.json(
      { error: "Username and password are required" },
      { status: 400 }
    );
  }

  try {
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
      console.error("[login] backend unreachable during provisioning:", err);
      return null;
    });

    if (provisionRes && !provisionRes.ok) {
      const body = await provisionRes.text().catch(() => "");
      console.error(`[login] provisioning returned ${provisionRes.status}:`, body);
    }

    return res;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Login failed";
    return NextResponse.json({ error: message }, { status: 401 });
  }
}
