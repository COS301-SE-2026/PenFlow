import SecurityAnalyst from "../../components/SecurityAnalyst";

export default async function SecurityAnalystPage({
  params,
}: {
  params: Promise<{ scan_id: string }>;
}) {
  const { scan_id } = await params;

  return <SecurityAnalyst scanId={scan_id} />;
}