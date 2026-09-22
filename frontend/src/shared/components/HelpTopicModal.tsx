"use client";

import { useEffect } from "react";
import type { HelpTopic } from "../helpContext";
import styles from "./HelpTopicModal.module.css";

interface HelpTopicModalProps {
    topic: HelpTopic | null;
    onClose: () => void;
}

export default function HelpTopicModal({topic, onClose}: HelpTopicModalProps) {
    useEffect(() => {
        if(!topic) return;
        const onKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, [topic, onClose]);

    if(!topic) return null;
    const accent = topic.accent ?? "info";
    const Icon = topic.icon;

    return (
        <>
            <button
                type="button"
                aria-label="Close help"
                className={styles.backdrop}
                onClick={onClose}
            />

            <div className={`${styles.modal} ${styles[`accent-${accent}`] ?? ""}`}
                role="dialog"
                aria-modal="true"
                aria-labelledby="help-topic-title"
                >
                    <div className={styles.header}>
                        <div className={styles.headerText}>
                            {Icon && (
                                <span className={`${styles.iconBadge} ${styles[`badge-${accent}`] ?? ""}`}>
                                    <Icon size={18} />
                                </span>
                            )}
                            <h2 id="help-topic-title" className={styles.title}>{topic.title}</h2>
                        </div>
                        <button type="button" className={styles.closeBtn} aria-label="Close" onClick = {onClose}>
                            &times;
                        </button>
                    </div>
                    <div className={styles.body}>{topic.body}</div>
                </div>
        </>
    );
}