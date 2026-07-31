import { NextResponse } from "next/server";

import { type TokenResponse } from "@/lib/keycloakService";

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

  res.cookies.set("id_token", tokens.id_token, {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax",
    maxAge: tokens.refresh_expires_in,
    path: "/",
  });
}