import {
    Bug,
    Crosshair,
    FileSearch,
    Fingerprint,
    Globe,
    Info,
    Lock,
    Network,
    ShieldAlert,
    ShieldCheck,
    type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { ScanSourceStatus } from "@/lib/scanService";

interface WorkerMeta {
    label: string;
    icon: LucideIcon;
}