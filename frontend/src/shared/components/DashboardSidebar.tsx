import Link from "next/link";

export default function DashboardSidebar() {
    return (
        <aside className = "dashboard-sidebar">
            <h2>PENFLOW</h2>

            <nav>
                <ul>
                    <li>
                        <Link href = "/dashboard">Dashboard</Link>
                    </li>
                    <li>
                        <Link href = "/scans">Scans</Link>
                    </li>
                    <li>
                        <Link href = "/scheduled-scans">Scheduled Scans</Link>
                    </li>
                    <li>
                        <Link href = "/history">History</Link>
                    </li>
                    <li>
                        <Link href = "/settings">Settings</Link>
                    </li>
                    <li>
                        <Link href = "/help">Help</Link>
                    </li>
                </ul>
            </nav>
            
        </aside>
    );
}