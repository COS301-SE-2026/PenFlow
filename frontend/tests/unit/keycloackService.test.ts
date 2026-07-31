//testing for auth function(login ,refresh ,logout, register)
//mock keycloak api resonse to verify behavior without making real clalls

import {
    refreshAccessToken,
} from "@/lib/keycloakService";


//keycloak endpoints used in the test:
const TOKEN_URL = "http://localhost:8080/realms/penflow/protocol/openid-connect/token";

//helper simplife mocking fetch reponse with custom status and body

function jsonResponse(body: unknown, ok = true, status =200){
return {
    ok,
    status,
    json:() => Promise.resolve(body),
}   as Response;
}

//reset all mock befroe each test to ensure clean state
beforeEach(()=>{
    jest.resetAllMocks();
});


//test refresh token
describe( "refresh token ",() =>{
it("refresh token grant and return a new token pair",async() =>{
   const tokens = {
      access_token: "newAccess",
      refresh_token: "newRefresh",
      expires_in: 900,
      refresh_expires_in: 1800,
    };

    const fetchSpy = jest
    .spyOn(global, "fetch")
    .mockResolvedValue(jsonResponse(tokens));

      //execute refresh
    const result = await refreshAccessToken("OldRefreshToken")

    //verify request sent to correct token endpoint
        expect(fetchSpy).toHaveBeenCalledWith(
      TOKEN_URL,
      expect.objectContaining({ method: "POST" })
    );
    //verify request body

    const body =(fetchSpy.mock.calls[0][1]?.body as URLSearchParams).toString();
    expect(body).toContain("grant_type=refresh_token");
    expect(body).toContain("refresh_token=OldRefreshToken");
    expect(result).toEqual(tokens);
    expect(result).toEqual(tokens);
});
//error when token expires
  it("throws when the refresh token is expired/invalid", async () => {
    jest.spyOn(global, "fetch").mockResolvedValue(
      jsonResponse({ error_description: "Token is not active" }, false, 400)
    );

    await expect(refreshAccessToken("expiredToken")).rejects.toThrow(
      "Token is not active"
    );
  });


});
