import { NextRequest, NextResponse } from "next/server";
import { LOGOUT_URL } from "@/lib/keycloakService";

const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? "penflow-web";
const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

export async function GET(req: NextRequest) {
  const idToken = req.cookies.get("id_token")?.value;

  const postLogoutRedirectUri = APP_URL;

  const logoutUrl = new URL(LOGOUT_URL);

  logoutUrl.searchParams.set(
    "post_logout_redirect_uri",
    postLogoutRedirectUri,
  );

  logoutUrl.searchParams.set(
    "client_id",
    CLIENT_ID,
  );

  if (typeof idToken === "string" && idToken.length > 0) {
    logoutUrl.searchParams.set(
      "id_token_hint",
      idToken,
    );
  }

  const res = NextResponse.redirect(logoutUrl);

  res.cookies.delete("access_token");
  res.cookies.delete("refresh_token");
  res.cookies.delete("id_token");
  res.cookies.delete("logged_in");
  
  return res;
}