import AssetsGrid from "../../components/AssetsGrid";
export default async function AssetsPage({params}: {params:Promise<{scan_id: string}>}){
    const {scan_id} = await params;
    return <AssetsGrid scanId = {scan_id} />;
}