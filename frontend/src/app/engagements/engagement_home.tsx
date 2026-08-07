//engagement home screen
"use client";

import { useState } from "react";
import { Eye, EyeOff, Scan, Plus, Trash2, CheckCircle2 } from "lucide-react";



//type declaration 
type EngagementType  = "black_box" | "grey_box" | "white_box";

type AssetType = "domain" | "ip" | "hostname" | "url";

interface Asset {
    id:string;
    type :AssetType;
    value :string;
}

const engagement_type_options:{
    value: EngagementType;
    label: string;
    description: string;
    icon : typeof EyeOff;
}[] = [
    {
        value: "black_box",
        label: "Black Box",
        description: "No internal knowledge or access is provided.Testers simulate an external attacker with no prior information.",
        icon : EyeOff,
    },
    {
        value: "grey_box",
        label: "Grey Box",
        description: "Partial knowledge is shared — e.g. limited credentials or architecture docs — simulating an attacker with some insider access.",
        icon: Eye,

    },

     {
        value: "white_box",
        label: "White Box",
        description: "Full knowledge and access, including source code and architecture, for a deep and thorough assessment.",
        icon: Scan,
    },

];

const asset_type_options:{value: AssetType; label:string } [] = [
    { value: "domain", label: "Domain" },
    { value: "ip", label: "IP Address" },
    { value: "hostname", label: "Hostname" },
    { value: "url", label: "URL" },


];