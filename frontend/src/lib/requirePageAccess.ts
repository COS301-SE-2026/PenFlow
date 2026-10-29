import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { isAppRole, ROLE_HOME, type AppRole } from "./routeAccess";

async function backendGet(
  path: string,
  token: string,
): Promise<Response | null> {
  try {
    const base = (
      process.env.API_URL ?? "http://localhost:3001"
    ).replace(/\/$/, "");

    return await fetch(`${base}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    return null;
  }
}

async function pageIdentity(): Promise<{
  role: AppRole;
  token: string;
}> {
  const store = await cookies();
  const token = store.get("access_token")?.value;

  if (!token) {
    redirect("/api/auth/login");
  }

  const response = await backendGet("/api/v1/users/me", token);

  if (response?.status === 401) {
    redirect("/api/auth/login");
  }

  if (!response?.ok) {
    redirect("/access-unavailable");
  }

  let body: unknown;

  try {
    body = await response.json();
  } catch {
    redirect("/access-unavailable");
  }

  if (
    !body ||
    typeof body !== "object" ||
    !("role" in body) ||
    !isAppRole(body.role)
  ) {
    redirect("/access-unavailable");
  }

  return { role: body.role, token };
}

export async function requirePageUser(): Promise<AppRole> {
  return (await pageIdentity()).role;
}

export async function requirePageRole(
  required: AppRole,
): Promise<void> {
  const identity = await pageIdentity();

  if (identity.role !== required) {
    redirect(ROLE_HOME[identity.role]);
  }

  if (required === "pentester") {
    const response = await backendGet(
      "/api/v1/pentester?limit=1&offset=0",
      identity.token,
    );

    if (response?.status === 401) {
      redirect("/api/auth/login");
    }

    if (!response?.ok) {
      redirect("/access-unavailable");
    }
  }
}