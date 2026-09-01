interface SidebarProfileFooterProps {
    name: string;
    role: string;
}

export default function SidebarProfileFooter ({ name, role }: SidebarProfileFooterProps){
    return (
        <div
             style={{
                    marginTop: "auto",
                    marginLeft: "16px",
                    marginRight: "16px",
                    marginBottom: "16px",
                    padding: "12px",
                    borderRadius: "9px",
                    border: "1px solid var(--col-edge)",
                    textAlign: "left",
                }}
        >
            <div style={{ fontWeight: 600 }}>{name}</div>
            <div style={{ fontSize: "12px", color: "rgba(229, 243, 255, 0.75)", marginTop: "3px" }}>{role}</div>
        </div>

    );
}