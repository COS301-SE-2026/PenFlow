import { redirect } from "next/navigation";

export default function RegisterPage() {
  redirect("/api/auth/register");
}