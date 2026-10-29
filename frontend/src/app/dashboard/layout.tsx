import type { ReactNode } from "react";
import { requirePageUser } from "@/lib/requirePageAccess";

export default async function AccountSectionLayout({
  children,
}: {
  children: ReactNode;
}) {
  await requirePageUser();

  return <>{children}</>;
}