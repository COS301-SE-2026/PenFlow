const KEYCLOAK_PUBLIC_URL = process.env.KEYCLOAK_PUBLIC_URL ?? "http://localhost:8080";
const KEYCLOAK_INTERNAL_URL = process.env.KEYCLOAK_INTERNAL_URL ?? KEYCLOAK_PUBLIC_URL;
const REALM = process.env.KEYCLOAK_REALM ?? "penflow";
const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? "penflow-web";

export const AUTHORIZATION_URL = `${KEYCLOAK_PUBLIC_URL}/realms/${REALM}/protocol/openid-connect/auth`;
export const TOKEN_URL = `${KEYCLOAK_INTERNAL_URL}/realms/${REALM}/protocol/openid-connect/token`;
export const LOGOUT_URL = `${KEYCLOAK_PUBLIC_URL}/realms/${REALM}/protocol/openid-connect/logout`;

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  id_token: string;
  expires_in: number;
  refresh_expires_in: number;
  token_type: string;
}

export async function exchangeAuthCode(
  code: string,
  codeVerifier: string,
  redirectUri: string,
): Promise<TokenResponse> {
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      code,
      redirect_uri: redirectUri,
      code_verifier: codeVerifier,
    }),
  });

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Authorization code exhange failed: ${err}`);
  }
  return res.json() as Promise<TokenResponse>;
}


//added refresh toekn  allow user don't have to reenter a possword in certain time
export async function refreshAccessToken(refreshToken: string):Promise<TokenResponse>
{
  const res = await fetch(TOKEN_URL,{
    method: "POST",
    headers: {"Content-Type":"application/x-www-form-urlencoded"},
    body:new URLSearchParams({
      grant_type: "refresh_token",
      client_id: CLIENT_ID,
      refresh_token:refreshToken
    }),
  });
  if(!res.ok){
    const err =await res.json().catch(()=>({})) as  Record<string,string>;
    throw new Error(err.error_description ?? "Failed to refresh session");
  }
  return res.json() as Promise<TokenResponse>;
}