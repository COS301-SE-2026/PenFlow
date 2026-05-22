import { NextResponse } from "next/server";

import { type TokenResponse } from "@/lib/keycloakService";

const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";

export async function createAuthResponse(tokens: TokenResponse): Promise<NextResponse> {
  const res = NextResponse.json({ success: true });

  const isProduction = process.env.NODE_ENV === "production";

  res.cookies.set("access_token", tokens.access_token, {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax",
    maxAge: tokens.expires_in,
    path: "/",
  });

  res.cookies.set("refresh_token", tokens.refresh_token, {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax",
    maxAge: tokens.refresh_expires_in,
    path: "/",
  });

  const provisionRes = await fetch(`${BACKEND_URL}/api/v1/users/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  }).catch((err: unknown) => {
    console.error("[auth] backend unreachable during provisioning:", err);
    return null;
  });

  if (provisionRes && !provisionRes.ok) {
    const body = await provisionRes.text().catch(() => "");
    console.error(`[auth] provisioning returned ${provisionRes.status}:`, body);
  }

  return res;
}
