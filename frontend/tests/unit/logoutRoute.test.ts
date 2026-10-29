/** @jest-environment node */

import { NextRequest } from "next/server";

jest.mock("../../src/lib/keycloakService", () => ({
    LOGOUT_URL: "https://auth.example.com/logout",
}));

import * as logoutRoute from "@/app/api/auth/logout/route";

test("logout uses POST, clears cookies, and redirects with 303", async () => {
    const response = await logoutRoute.POST(
        new NextRequest(
            "http://localhost:3000/api/auth/logout",
            {
                method: "POST",
                headers: {
                    Cookie: "access_token=test; id_token=example",
                },
            },
        ),
    );

    expect(response.status).toBe(303);
    expect(
        new URL(response.headers.get("Location")!).origin,
    ).toBe("https://auth.example.com");
    expect(
        response.cookies.get("access_token")?.value,
    ).toBe("");
    expect(logoutRoute).not.toHaveProperty("GET");
});