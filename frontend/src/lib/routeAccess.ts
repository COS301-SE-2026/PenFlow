export type AppRole = "client" | "pentester" | "service_delivery";

export const ROLE_HOME: Record<AppRole, string> = {
  client: "/",
  pentester: "/pentesting/console/my-engagements",
  service_delivery: "/service-delivery/dashboard",
};

export function isAppRole(value: unknown): value is AppRole {
  return (
    value === "client" ||
    value === "pentester" ||
    value === "service_delivery"
  );
}

function within(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

const ROLE_SECTIONS: ReadonlyArray<readonly [string, AppRole]> = [
  ["/service-delivery", "service_delivery"],
  ["/pentesting/console", "pentester"],
  ["/pentesting/engagement", "client"],
  ["/pentesting/messages", "client"],
  ["/engagement_request", "client"],
];

const ACCOUNT_SECTIONS = [
  "/domains",
  "/history",
  "/scheduled-scans",
  "/dashboard",
];

export function canVisitPage(path: string, role: unknown): boolean {
  const required = ROLE_SECTIONS.find(([prefix]) => within(path, prefix));

  if (required) {
    return isAppRole(role) && role === required[1];
  }

  if (ACCOUNT_SECTIONS.some((prefix) => within(path, prefix))) {
    return isAppRole(role);
  }

  return true;
}