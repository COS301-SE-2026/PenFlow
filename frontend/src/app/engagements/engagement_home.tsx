//engagement home screen
"use client";

import { useState } from "react";
import { Eye, EyeOff, Scan, Plus, Trash2, CheckCircle2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/shared/components/ui/button";
import { Separator } from "@/shared/components/ui/separator";
import { cn } from "@/lib/utils";


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

export default function EngagementHome() {
    const[engagementType,setEngagementType] = useState<EngagementType | null>(null);
   
    const [objective ,setObjective] = useState("");
    const [startDate , setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [constraints, setConstraints] = useState("");
    const [primaryContact, setPrimaryContact] = useState("");

    const [assetType, setAssetType] = useState<AssetType>("domain");
    const [assetValue, setAssetValue] = useState("");
    const [assets, setAssets] = useState<Asset[]>([]);

    const [submitted, setSubmitted] = useState(false) ;

    function handle_add_asset(){
        const value =assetValue.trim();
        if(!value)return;

        setAssets((prev) => [...prev, { id: crypto.randomUUID(), type: assetType, value}]);
        setAssetValue("");
    }
    function handle_remove_asset(id:string){
        setAssets((prev)=>prev.filter((a)=>a.id!==id));
    }
    function handle_submit(){   
        setSubmitted(true);
    }
     const can_submit = engagementType !== null && objective.trim().length > 0 && assets.length > 0;

    return(
        <div className="mx-auto flex max-w-4xl flex-col gap-8 px-4 py-10 text-lg">
            <div className="flex flex-col gap-2">
              <h1 className="text-4xl font-bold text-foreground">Engagement Request</h1>
               <p className="text-lg text-muted-foreground">
                Scope out a new penetration testing engagement — choose an engagement type, fill in the
                scoping questionnaire, and declare the assets that are in scope.
               </p>
            </div>

            {submitted && (
            <Card className = "border-brand-success/40 bg-brand-success/10">
                <CardContent className="flex items-center gap-3 py-4">
                    <CheckCircle2 className="size-6 shrink-0 text-brand-success" />
                    <p className="text-lg text-foreground">
                        Engagement request captured.
                    </p>
                </CardContent>
            </Card>
            
            
            )}
        </div>
    )
}