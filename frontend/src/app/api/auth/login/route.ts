import { NextResponse } from "next/server";

import { AUTHORIZATION_URL } from "@/lib/keycloakService";
import { generateCodeChallenge, generateCodeVerifier, generateState } from "@/lib/pkce";

const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? "penflow-web";
const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

export async function GET() {
  const verifier = generateCodeVerifier();
  const challenge = generateCodeChallenge(verifier);
  const state = generateState();

  const redirectUri = `${APP_URL}/api/auth/callback`;

  const authUrl = new URL(AUTHORIZATION_URL);

  authUrl.searchParams.set("client_id", CLIENT_ID);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", "openid profile email");
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("code_challenge", challenge);
  authUrl.searchParams.set("code_challenge_method", "S256");

  const resp = NextResponse.redirect(authUrl);

  const secure = process.env.NODE_ENV === "production";

  resp.cookies.set("oauth_state", state, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });

  resp.cookies.set("pkce_verifier", verifier, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });

  return resp;
}