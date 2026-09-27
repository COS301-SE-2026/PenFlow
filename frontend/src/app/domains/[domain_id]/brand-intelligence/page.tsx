
import Link from "next/link";

import DashboardLayout from "@/shared/components/DashboardLayout";
import PageHero from "@/shared/components/PageHero";


interface BrandIntelligencePageProps
{
   params: Promise<{ domain_id: string }>;
   searchParams: Promise<{ domain?: string }>;
}


//first getting the correct domain page working before connecting the API
export default async function BrandIntelligencePage
(
   { params, searchParams }: BrandIntelligencePageProps
)

{
   const { domain_id } = await params;
   const { domain } = await searchParams;

   return (
      <DashboardLayout>
         <div className="flex flex-col gap-5">

            <PageHero title="BRAND INTELLIGENCE" />
            <Link
               href="/domains"
               className="text-sm text-brand-cyan hover:underline"
            >
               Back to Domains
            </Link>

            <div className="rounded-lg border border-brand-panel-border bg-brand-panel p-6">
               <h2 className="text-xl font-semibold text-foreground">
                  {domain ?? domain_id}
               </h2>

               <p className="mt-3 text-sm text-muted-foreground">
                  Brand monitoring will appear here once connected to
                  the PenFlow backend.
               </p>
            </div>

         </div>
      </DashboardLayout>
   );
}
