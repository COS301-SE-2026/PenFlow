import ScanResultsOverview from "../components/ScanResultsOverview";
export default async function Page({params}: {params: Promise<{scan_id: string}>}) {
    const {scan_id} = await params;
    return <ScanResultsOverview scanId = {scan_id} />;
}