import {Suspense} from "react";
import FindingsGrid from "../../components/FindingsGrid";
export default async function FindingsPage({params}: {params: Promise<{scan_id: string}>}) {
    const {scan_id} = await params;
    return (
        <Suspense fallback = {<div>Loading findings...</div>}>
            <FindingsGrid scanId={scan_id} />
        </Suspense>
    )
}