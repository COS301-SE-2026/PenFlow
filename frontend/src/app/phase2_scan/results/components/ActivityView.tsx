"use client"

import { useEffect, useState } from "react";

import { fetchScanStatus, type RealTimeScanStatus } from "@/lib/scanService";
import WorkerStatusGrid from "./WorkerStatusGrid";

const scanTypeLabel: Record<string, string> = {
    active_vulnerability: "Active Vulnerability Scan",
    passive_ctem: "Passive Reconnaissance",
};