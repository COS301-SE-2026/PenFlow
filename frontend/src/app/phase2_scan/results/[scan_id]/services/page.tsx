import ServicesView from "../../components/ServicesView";
export default async function ServicesPage({params}: {params:Promise<{scan_id: string}>}) {
    const {scan_id} = await params;
    return <ServicesView scanId={scan_id}/>
}