import { Suspense } from "react";
import AssetsGrid from "../../components/AssetsGrid";
export default async function AssetsPage({params}: {params:Promise<{scan_id: string}>}){
    const {scan_id} = await params;
    return (
        <Suspense fallback={<div>Loading assets...</div>}>
            <AssetsGrid scanId = {scan_id} />
        </Suspense>
    );
}
