import { proxyToUsersApi } from "@/lib/usersBackend";

export async function GET() { 
    return proxyToUsersApi("/me");
}