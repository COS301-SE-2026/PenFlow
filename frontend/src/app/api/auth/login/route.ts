import { NextRequest, NextResponse } from "next/server";

import { createAuthResponse } from "@/lib/authSession";
import { loginWithPassword } from "@/lib/keycloakService";

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
    return createAuthResponse(tokens);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Login failed";
    return NextResponse.json({ error: message }, { status: 401 });
  }
}
