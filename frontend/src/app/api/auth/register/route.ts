/*import { NextRequest, NextResponse } from "next/server";

import { createAuthResponse } from "@/lib/authSession";
import { loginWithPassword, registerUser } from "@/lib/keycloakService";

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
    return createAuthResponse(tokens);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Registration failed";
    const status = message.includes("already exists") ? 409 : 400;
    return NextResponse.json({ error: message }, { status });
  }
}
*/