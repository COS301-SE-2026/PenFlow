import styles from "./PageHero.module.css";
interface  PageHeroProps {
    title: string;
}

export default function PageHero({title} : PageHeroProps) {
    return (
        <section className={styles.hero}>
            <div className={styles.heroTextWrap}>
                <h1>{title}</h1>
            </div>
            <div className= {styles.waterline} aria-hidden = "true">
                <svg
                    viewBox = " 0 0 1420 200"
                    xmlns = "http://www.w3.org/2000/svg"
                    style = {{position: "absolute", inset: 0, width: "100%", height: "100%"}}
                    preserveAspectRatio = "none"
                >
                    <path d="M0,40 Q180,80 360,40 T720,40 T1080,40 T1440,40 V200 H0 Z" fill="rgba(43,180,220,0.35)" />
                    <path d="M0,90 Q200,130 400,90 T800,90 T1200,90 T1440,90 V200 H0 Z" fill="rgba(15,37,75,0.9)" />
                    <path d="M0,150 Q220,178 440,150 T880,150 T1320,150 T1440,150 V200 H0 Z" fill="#091628" />
                </svg>
            </div>
        </section>
    );
}