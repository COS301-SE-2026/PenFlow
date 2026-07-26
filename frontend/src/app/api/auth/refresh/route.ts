//refresher logic 
//exchange refresh token to get a new access token pair

import { NextRequest ,NextResponse } from "next/server";

import { setAuthCookies } from "@/lib/authSession";
import { refreshAccessToken } from "@/lib/keycloakService";

export async function POST(req:NextRequest) {
    // extract the refresh token from http-only cookie
    const refreshToken = req.cookies.get("refresh_token")?.value;
    
    if(!refreshToken){
        return NextResponse.json({error: "No refresh token"},{status:401}); 
    }

    try{
        //call keycloack for new token
        const tokens = await refreshAccessToken(refreshToken);
        const res  = NextResponse.json({success : true });
        //set new cookies
        setAuthCookies(res,tokens);
        return res;
    }catch(err){
        //error handling
        //oncer failure , clear all auth auth cookie to force re-login
        const message = err instanceof Error ? err.message : "Refresh failed";
        const res = NextResponse.json({error:message},{status:401})
        //clear all auth cookie on failure
        res.cookies.delete("access_token");
        res.cookies.delete("refresh_token");
        res.cookies.delete("logged_in");
        return res;
    }
}