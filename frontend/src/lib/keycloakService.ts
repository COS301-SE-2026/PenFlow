const KEYCLOAK_URL = process.env.KEYCLOAK_URL ?? "http://localhost:8080";
const REALM = process.env.KEYCLOAK_REALM ?? "penflow";
const CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID ?? "penflow-frontend";
const CLIENT_SECRET = process.env.KEYCLOAK_CLIENT_SECRET ?? "";
const ADMIN_USER = process.env.KEYCLOAK_ADMIN ?? "admin";
const ADMIN_PASSWORD = process.env.KEYCLOAK_ADMIN_PASSWORD ?? "";

const TOKEN_URL = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`;
const LOGOUT_URL = `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/logout`;

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  refresh_expires_in: number;
}

export async function loginWithPassword(
  username: string,
  password: string
): Promise<TokenResponse> {
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "password",
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      username,
      password,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as Record<string, string>;
    throw new Error(err.error_description ?? "Invalid credentials");
  }

  return res.json() as Promise<TokenResponse>;
}

export async function logoutSession(refreshToken: string): Promise<void> {
  await fetch(LOGOUT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      refresh_token: refreshToken,
    }),
  });
}

async function getAdminToken(): Promise<string> {
  const res = await fetch(
    `${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "password",
        client_id: "admin-cli",
        username: ADMIN_USER,
        password: ADMIN_PASSWORD,
      }),
    }
  );

  if (!res.ok) throw new Error("Failed to obtain admin token");
  const data = await res.json() as Record<string, string>;
  return data.access_token;
}

export async function registerUser(
  username: string,
  email: string,
  password: string,
  firstName: string,
  lastName: string
): Promise<void> {
  const adminToken = await getAdminToken();

  const res = await fetch(`${KEYCLOAK_URL}/admin/realms/${REALM}/users`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${adminToken}`,
    },
    body: JSON.stringify({
      username,
      email,
      firstName,
      lastName,
      enabled: true,
      emailVerified: true,
    }),
  });

  if (res.status === 409) throw new Error("Username or email already exists");
  if (!res.ok) throw new Error("Failed to create account");

  const location = res.headers.get("Location") ?? "";
  const userId = location.split("/").pop();
  if (!userId) throw new Error("Failed to retrieve new user ID");

  const pwRes = await fetch(
    `${KEYCLOAK_URL}/admin/realms/${REALM}/users/${userId}/reset-password`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${adminToken}`,
      },
      body: JSON.stringify({ type: "password", value: password, temporary: false }),
    }
  );

  if (!pwRes.ok) throw new Error("Failed to set account password");
}
