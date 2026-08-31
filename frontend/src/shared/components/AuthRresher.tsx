//authRefresher - client side component that proactively refresh auth

//purpose:
//keep ther user session alive by refreshing access token before it expire
//Dynamic Refresh Timing refresh at 80% before expire 
//ensures the new token is obtained before one expires
//80% because it gives  20% buffer time to prevent race condtions


"use client";

import { useEffect } from "react";


//access token configure

const REFRESH_BUFFER_MS = 60 * 1000;

const FALLBACK_LIFESPAN_SECONDS =
    Number(process.env.NEXT_PUBLIC_ACCESS_TOKEN_LIFESPAN_SECONDS) || 900;
    
function getCookie(name: string): string | null {
    const cookie = document.cookie.split("; ")
    .find((item) => item.startsWith(`${name}=`));

    return cookie ? cookie.substring(name.length + 1): null;
}


function isLoggedIn(): boolean{
    return getCookie("logged_in") !== null;
}

function getAccessTokenExpiry(): number | null {
    const value = getCookie("access_token_expires_at");

    if(!value) {
        return null;
    }

    const expiry = Number(value);

    return Number.isFinite(expiry) ? expiry : null;
}
//keep users alive with user interacting
export default function AuthRefresher(){
    useEffect(()=>{
        let timeoutId: ReturnType<typeof setTimeout> | null = null;
        let cancelled = false;

        const refresh = async () => {
            if(cancelled || !isLoggedIn()) {
                return;
            }

            try {
                await navigator.locks.request(
                    "penflow-auth-refresh",
                    async () => {
                        if(cancelled || !isLoggedIn()) {
                            return;
                        }

                        const expiresAt = getAccessTokenExpiry();

                        if(expiresAt !== null && expiresAt - Date.now() > REFRESH_BUFFER_MS) {
                            scheduleRefresh();
                            return;
                        }

                        const response = await fetch("/api/auth/refresh", {method: "POST"});

                        if(!response.ok) {
                            window.location.href = "/api/auth/logout";
                            return;
                        }

                        scheduleRefresh();
                    }                
                );
            } catch {
                window.location.href = "/api/auth/logout";
            }
        };

        const scheduleRefresh = () => {
            if(cancelled || !isLoggedIn()) {
                return;
            }

            if(timeoutId !== null) {
                clearTimeout(timeoutId);
            }

            const expiresAt = getAccessTokenExpiry();

            let delay: number;

            if(expiresAt !== null) {
                delay = Math.max(expiresAt - Date.now() - REFRESH_BUFFER_MS, 0);
            }
            else {
                delay = FALLBACK_LIFESPAN_SECONDS * 1000 * 0.8;
            }

            timeoutId = setTimeout(refresh, delay);
        };


        scheduleRefresh();

        return () => {
            cancelled = true;

            if(timeoutId !== null) {
                clearTimeout(timeoutId);
            }
        };
    } , []);

    return null;
}
