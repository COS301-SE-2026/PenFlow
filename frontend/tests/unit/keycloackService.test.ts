//testing for auth function(login ,refresh ,logout, register)
//mock keycloak api resonse to verify behavior without making real clalls

import {
    loginWithPassword,
    refreshAccessToken,
    logoutSession,
    registerUser,
} from "@/lib/keycloakService";

//keycloak endpoints used in the test:
const Token_URL = "http://localhost:8080/realms/penflow/protocol/openid-connect/token";
const LOGOUT_URL = "http://localhost:8080/realms/penflow/protocol/openid-connect/logout";

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

//login tests

describe("LoginWithPassword",()=>{
    //mock success  token response
    const tokens ={
        access_token :"accesss123",
        refresh_token: "refresh123",
        expires_in: 900, //15min access token
        refresh_expires_in: 1800 //30min refresh token
    };
    it("send password grant to keycloak and return tokens",async() => {
    const fetchSpy = jest.spyOn(global,"fetch") 
    .mockResolvedValue(jsonResponse(tokens));

    //cal function with test credentials
    const result = await loginWithPassword("1234","1234");

    //verify request body 
    const body = (fetchSpy.mock.calls[0][1]?.body as URLSearchParams).toString();
    expect(body).toContain("grant_type=password")
    expect(body).toContain("username=1234");
    expect(body).toContain("password=1234");
      // Verify returned tokens match expected
     expect(result).toEqual(tokens);
})
     it("throws with Keycloak's error_description on bad credentials", async () => {
    // Mock 401 error response from Keycloak
    jest.spyOn(global, "fetch").mockResolvedValue(
      jsonResponse({ error_description: "Invalid user credentials" }, false, 401)
    );

    // Verify the error is thrown with the correct message
    await expect(loginWithPassword("1234", "wrong")).rejects.toThrow(
      "Invalid user credentials"
    );
  });

}
);

