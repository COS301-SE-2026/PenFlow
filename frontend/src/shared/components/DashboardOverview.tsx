import DashboardHeader from "./DashboardHeader";
import Link from "next/link"
export default function DashboardOverview() {
    return (
        <>
            <DashboardHeader />

            <section className = "dashboard-section">

                <div className = "dashboard-section-header">
                    <div>
                        <h2> Quick Actions </h2>
                        <p> Access Commonly used features. </p>
                    </div>
                </div>

                <div className = "dashboard-quick-actions">

                    <div className = "dashboard-action-card">
                        <h3> New Scan </h3>
                        <p> Start a security scan for a domain. </p>
                        <Link href = "/scans"> Start scan </Link>
                    </div>

                    <div className = "dashboard-action-card">
                        <h3> Verify Domain </h3>
                        <p> Verify Ownership of a new domain. </p>
                        <Link href = "/domains"> Verify domain </Link>
                    </div>

                    <div className = "dashboard-action-card">
                        <h3> Schedule Scan </h3>
                        <p> Configure a recurring security scan. </p>
                        <Link href = "/scheduled-scans"> Schedule scan </Link>
                    </div>

                    <div className = "dashboard-action-card">
                        <h3> View History </h3>
                        <p> Browse previously configured scans. </p>
                        <Link href = "/history"> View history </Link>
                    </div>

                </div>

            </section>

            <section className = "dashboard-insights">

                <div className = "dashboard-card dashboard-risky-domains">
                    <div className = "dashboard-card-header">
                        <div>
                            <h2> Top Risky Domains </h2>
                            <p> Domains with the highest current risk scores. </p>
                        </div>

                        <Link href = "/domains "> View all domains </Link>
                    </div>  

                    <div> Top risky domains content </div>  
                </div>

                <div className = "dashboard-card dashboard-security-trend">
                    <div className = "dashboard-card-header">
                        <div>
                            <h2> Security Trend </h2>
                            <p> Compared with the previous scan cycle. </p>
                        </div>

                        <button type = "button"> Last 30 days </button>
                    </div>  

                    <div> Security trend content </div>  
                </div>

            </section>

            <section className = "dashboard-section">
                <div className = "dashboard-section-header">
                    <div>
                        <h2> Security Overview </h2>
                        <p> Current scan and finding activity. </p>
                    </div>
                </div>

                <div className = "dashboard-summary-grid">
                    <div className = "dashboard-card dashboard-summary-card">
                        <span className = "dashboard-card-label">
                            Running Scans 
                        </span>

                        <strong className = "dashboard-card-value"> 2 </strong>

                        <p> Scans currently in progress. </p>

                        <Link href = "/scans?status=running"> View running scans </Link>
                    </div>

                    <div className = "dashboard-card dashboard-summary-card">
                        <span className = "dashboard-card-label">
                            Open Critical Findings
                        </span>

                        <strong className = "dashboard-card-value"> 8 </strong>

                        <p> Critical findings requiring attention. </p>

                        <Link href = "/findings?severity=critical"> View findings </Link>
                    </div>

                    <div className = "dashboard-card dashboard-summary-card">
                        <span className = "dashboard-card-label">
                            Latest Completed Scan
                        </span>

                        <strong className = "dashboard-card-value"> example.com </strong>

                        <p> Completed 15 minutes ago. </p>

                        <Link href = "/scans"> View results </Link>
                    </div>

                    <div className = "dashboard-card dashboard-summary-card">
                        <span className = "dashboard-card-label">
                            Next Scheduled Scan
                        </span>

                        <strong className = "dashboard-card-value"> Today, 16:00 </strong>

                        <p> Weekly external scan. </p>

                        <Link href = "/scheduled-scans"> View schedule </Link>
                    </div>

                </div>
            </section>
        </>
    );
}