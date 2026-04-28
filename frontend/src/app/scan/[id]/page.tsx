// Minimilast version made just so pnpm commands could be tested

export default async function ScanDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <div>Scan Detail: {id}</div>;
}
