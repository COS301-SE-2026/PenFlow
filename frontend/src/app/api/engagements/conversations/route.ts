import { NextRequest } from "next/server";
import { proxyToEngagementsApi } from "@/lib/engagementsBackend";

export async function GET(request: NextRequest) {
  return proxyToEngagementsApi(
    `/conversations?${request.nextUrl.searchParams.toString()}`,
  );
}