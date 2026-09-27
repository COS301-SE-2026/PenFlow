import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/authenticatedBackend";
import { isValidScanId } from "@/lib/scansBackend";

interface RouteContext {
  params: Promise<{ scan_id: string }>;
}

export async function POST(
  _request: Request,
  context: RouteContext,
) {
  const { scan_id } = await context.params;

  if(!isValidScanId(scan_id)) {
    return NextResponse.json(
      { detail: "Invalid scan id" },
      { status: 400 },
    );
  }

  return authenticatedBackendRequest({
    path: `/api/v1/rag/scans/${scan_id}/index`,
    init: {
      method: "POST",
    },
  });
}