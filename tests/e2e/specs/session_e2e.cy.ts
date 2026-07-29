//test the access key and refresh key 


//decode the jwt
function decodeJWTexp(token:string): number  {
    const payload = JSON.parse(atob(token.split(".")[1])) as
    { exp: number };
    return payload.exp;

}

describe("Session LifeTime",() => {
    it("report how long a user has before toekn expiry",()=>{
        cy.login("1234", "1234");

        cy.getCookie("access_token").then((accessCookie) => {
        cy.getCookie("refresh_token").then((refreshCookie) => {
        const now = Math.floor(Date.now() / 1000); //convert mili second to second

        const accessCookieTtl = (accessCookie!.expiry ?? 0) - now;//browser side
        const accessJwtTtl = decodeJWTexp(accessCookie!.value) - now; //token side
        const refreshCookieTtl = (refreshCookie!.expiry ?? 0) - now;

        cy.log(`Access token cookie expires in: ${accessCookieTtl}s`);
        cy.log(`Access token JWT 'exp' claim in: ${accessJwtTtl}s`);
        cy.log(`Refresh token cookie expires in: ${refreshCookieTtl}s (${(refreshCookieTtl / 60).toFixed(1)} min)`);


      });
    });
  });
})
