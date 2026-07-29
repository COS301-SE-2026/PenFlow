import { NextResponse } from "next/server";

import { type TokenResponse } from "@/lib/keycloakService";

const BACKEND_URL = process.env.API_URL ?? "http://localhost:3001";

export function setAuthCookies(res: NextResponse, tokens: TokenResponse): void {

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
   // Tied to the refresh session not the access token so the navbar does not log out user when time reach
  res.cookies.set("logged_in", "1", {
    httpOnly: false,
    secure: isProduction,
    sameSite: "lax",
    maxAge: tokens.refresh_expires_in,
    path: "/",
  });

}

export async function createAuthResponse(tokens: TokenResponse): Promise<NextResponse> {
  const res = NextResponse.json({ success: true });
  setAuthCookies(res, tokens);
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