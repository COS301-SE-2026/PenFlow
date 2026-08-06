import {  NextResponse } from "next/server";

import {AUTHORIZATION_URL} from  "@/lib/keycloakService"
import { generateCodeChallenge,generateCodeVerifier,generateState } 
from "@/lib/pkce";

const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? "penflow-web"
const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

export async function  GET() {
  //PKCE(proof key for key exchange) Security Generation
  const verifier = generateCodeVerifier(); //random secret string
  const challenge = generateCodeChallenge(verifier); //hashed verision of verifier
  const state = generateState() //csrf protection token


// Keycloak Registration URL 
const redirectUri = `${APP_URL}/api/auth/callback`;
const registerUrl = new URL(AUTHORIZATION_URL.replace("/auth", "/registrations"));

// OAuth Parameters 
registerUrl.searchParams.set("client_id", CLIENT_ID);
registerUrl.searchParams.set("response_type", "code"); 
registerUrl.searchParams.set("scope", "openid profile email");
registerUrl.searchParams.set("redirect_uri", redirectUri); 
registerUrl.searchParams.set("state", state); 
registerUrl.searchParams.set("code_challenge", challenge); 
registerUrl.searchParams.set("code_challenge_method", "S256")

//Store Security Tokens as Cookies
const resp=NextResponse.redirect(registerUrl);
const secure=process.env.NODE_ENV ==="production";


resp.cookies.set("oauth_state", state, { httpOnly: true, secure, sameSite: "lax", path: "/", maxAge: 900 }); //900 secs
resp.cookies.set("pkce_verifier", verifier, { httpOnly: true, secure, sameSite: "lax", path: "/", maxAge: 900 });


  return resp;
}
