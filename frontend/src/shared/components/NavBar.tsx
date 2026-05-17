import Link from "next/link";
import Image from "next/image";
import brocodeLogo from "@/app/images/images/BroCode logo.png";
import bluevisionLogo from "@/app/images/images/Bluevision logo.png";

export default function NavBar() {
  return (
    <nav className="topbar">
      <div className="logoPanel">
        <Image src={bluevisionLogo} alt="Bluevision" width={80} height={48} style={{ width: "auto", height: 48 }} />
        <div className="logoDivider" />
        <Image src={brocodeLogo} alt="BroCode" width={80} height={48} style={{ width: "auto", height: 48 }} />
      </div>

      <div className="topnav">
        <Link href="/login" className="nav-link">LOGIN</Link>
        <Link href="/" className="nav-link">HOME</Link>

      </div>

    </nav>
  );
}
