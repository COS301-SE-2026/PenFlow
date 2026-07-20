import { NextRequest, NextResponse } from "next/server";
import { logoutSession } from "@/lib/keycloakService";

export async function GET(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value;
  
  if (refreshToken) {
    await logoutSession(refreshToken).catch(() => {});
  }
  
  const res = NextResponse.redirect(new URL("/", req.url));
  res.cookies.delete("access_token");
  res.cookies.delete("refresh_token");
  res.cookies.delete("logged_in");
  return res;
}