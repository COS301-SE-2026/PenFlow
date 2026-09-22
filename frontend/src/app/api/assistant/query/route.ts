import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";

export async function POST(request: Request) {
  const body = await request.text();

  return authenticatedBackendRequest({
    path: "/api/v1/assistant/query",
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body,
    },
  });
}