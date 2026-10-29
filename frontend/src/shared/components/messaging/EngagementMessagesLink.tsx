import Link from "next/link";
import type { MessagingRole } from "./inbox";

const inboxPaths: Record<MessagingRole, string> = {
  client: "/pentesting/messages",
  pentester: "/pentesting/console/messages",
  service_delivery: "/service-delivery/messages",
};

export default function EngagementMessagesLink({
  role,
  engagementId,
  available = true,
}: {
  role: MessagingRole;
  engagementId: string;
  available?: boolean;
}) {
  if (!available) {
    return (
      <span
        className="text-sm text-muted-foreground"
        aria-disabled="true"
      >
        Messaging available once Service Delivery is assigned
      </span>
    );
  }

  const query = new URLSearchParams({
    engagement: engagementId,
  });

  return (
    <Link
      href={`${inboxPaths[role]}?${query}`}
      className="rounded-lg border border-brand-cyan/45 bg-brand-cyan/10 px-4 py-2.5 text-sm font-semibold text-brand-cyan no-underline hover:bg-brand-cyan/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-cyan"
    >
      Open messages
    </Link>
  );
}