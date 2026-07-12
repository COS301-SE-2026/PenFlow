import Link from "next/link";

interface DashboardTabItems {
    scanId?: string;
    activeTab?: "overview" | "findings" | "assets" | "services" | "reports";
}

export default function DashboardTabs({
    scanId = "demo-scan",
    activeTab = "overview",
}: DashboardTabItems) {
    return (
        <nav className = "dashboard-tabs" aria-label = "Scan sections">
            <Link
                href = {`/dashboard/${scanId}`}
                className = {`dashboard-tab ${
                    activeTab === "overview" ? "dashboard-tab-active": ""
                }`}
            >
                Overview
            </Link>

            <Link
                href = {`/dashboard/${scanId}/findings`}
                className = {`dashboard-tab ${
                    activeTab === "findings" ? "dashboard-tab-active": ""
                }`}
            >
                Findings
            </Link>

            <Link
                href = {`/dashboard/${scanId}/assets`}
                className = {`dashboard-tab ${
                    activeTab === "assets" ? "dashboard-tab-active": ""
                }`}
            >
                Assets
            </Link>

            <Link
                href = {`/dashboard/${scanId}/services`}
                className = {`dashboard-tab ${
                    activeTab === "services" ? "dashboard-tab-active": ""
                }`}
            >
                Services
            </Link>

            <Link
                href = {`/dashboard/${scanId}/reports`}
                className = {`dashboard-tab ${
                    activeTab === "reports" ? "dashboard-tab-active": ""
                }`}
            >
                Reports
            </Link>
        </nav>
    );
}