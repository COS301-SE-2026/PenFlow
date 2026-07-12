import DashboardHeader from "./DashboardHeader";
import DashboardTabs from "./DashboardTabs";

export default function DashboardOverview() {
    return (
        <>
            <DashboardHeader />
            <DashboardTabs />

            <section className = "dashboard-overview">
                <div>Risk Card</div>
                <div>Statistics</div>
                <div>Top Findings</div>
                <div>Asset Summary</div>
                <div>Service Summary</div>
                <div>Scan Timeline</div>
            </section>
        </>
    );
}