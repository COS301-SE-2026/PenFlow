interface DashboardHeaderName {
    userName?: string;
}

export default function DashboardHeader({
    userName = "Mock-User",
}: DashboardHeaderName) {
    return (
        <header className = "dashboard-header">
            <div>
                <h1> Welcome back, { userName} </h1>
                <p> Here&apos;s what&apos;s happening with your security posture.</p>
            </div>

            <div className = "dashboard-header-actions">
                <button type = "button" aria-label = "View Notifications">
                    Notifications
                </button>

                <button type = "button">
                    Organisation
                </button>
            </div>
        </header>
    );
}