import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";
import { isValidScanId } from "@/lib/scansBackend";

interface RouteContext {
  params: Promise<{ scan_id: string}>;
}

export async function POST(
  request: Request,
  context: RouteContext,
) {
  const { scan_id } = await context.params;

  if (!isValidScanId(scan_id)) {
    return NextResponse.json(
      { detail: "Invalid scan id" },
      { status: 400 },
    );
  }

  const body = await request.text();

  return authenticatedBackendRequest({
    path: `/api/v1/rag/scans/${scan_id}/ask`,
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body,
    },
  });
}
