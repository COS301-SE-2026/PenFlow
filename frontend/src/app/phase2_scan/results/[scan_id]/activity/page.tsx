import ActivityView from "../../components/ActivityView";
export default async function ActivityPage ({params} : {params: Promise<{scan_id: string}>}) {
    const {scan_id} = await params;
    return <ActivityView scanId={scan_id}/>
}