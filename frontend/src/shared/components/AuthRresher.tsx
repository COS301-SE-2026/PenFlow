//authRefresher - client side component that proactively refresh auth

//purpose:
//keep ther user session alive by refreshing access token before it expire
//Dynamic Refresh Timing refresh at 80% before expire 
//ensures the new token is obtained before one expires
//80% because it gives  20% buffer time to prevent race condtions


"use client";

import { useEffect } from "react";


//access token configure

const ACCESS_TOKEN_LIFESPAN_SECONDS =
    Number(process.env.NEXT_PUBLIC_ACCESS_TOKEN_LIFESPAN_SECONDS) || 300;
    
const REFRESH_INTERVAL_MS = ACCESS_TOKEN_LIFESPAN_SECONDS *1000*0.8;;


function isLoggedIn(): boolean{

    return document.cookie.split("; ").some((cookie) =>
      cookie.startsWith("logged_in=")  
    );
}
//keep users alive with user interacting
export default function AuthRefresher(){
    useEffect(()=>{
        const tick = () =>{
            if(!isLoggedIn()) return;
            //silent failure- will retry on next interval
            fetch("/api/auth/refresh",{method:"POST"}).catch(()=>{});

            
        }
            const id = setInterval(tick,REFRESH_INTERVAL_MS);
            return () => clearInterval(id);

    } , []);
    
    return null;

}
