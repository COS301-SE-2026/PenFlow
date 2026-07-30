//testing for auth function(login ,refresh ,logout, register)
//mock keycloak api resonse to verify behavior without making real clalls
/*
import {
    loginWithPassword,
    logoutSession,
    refreshAccessToken,
    registerUser,
    // registerUser,
} from "@/lib/keycloakService";


//keycloak endpoints used in the test:
const TOKEN_URL = "http://localhost:8080/realms/penflow/protocol/openid-connect/token";
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
        access_token :"access123",
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
    expect(body).toContain("grant_type=password");
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

//test logout
describe("Logout session",() =>{
  it("posts the refresh token to Keycloak's logout endpoint",async()=>{
    const fetchSpy = jest
    .spyOn(global, "fetch")
    .mockResolvedValue(jsonResponse({}));

    await logoutSession("someRefreshToken")


    expect(fetchSpy).toHaveBeenCalledWith(
    LOGOUT_URL,
    expect.objectContaining({ method: "POST" })
    );

    //verify logout is included in the request body
    const body = (fetchSpy.mock.calls[0][1]?.body as URLSearchParams).toString();
    expect(body).toContain("refresh_token=someRefreshToken");
  });

});

//test register 
describe("register User",() =>{
it("gets admin key ,create user,set their password",async ()=>{
  const fetchSpy =jest
  .spyOn(global ,"fetch")
  .mockImplementationOnce(()=>
  Promise.resolve(jsonResponse({access_token : "adminToken"}))
  )//1. get admin key

    .mockImplementationOnce(()=>
     Promise.resolve({
          ok: true,
          status: 201,
          headers: new Headers({
            Location: "http://localhost:8080/admin/realms/penflow/users/new-user-id",
          }),
          json: () => Promise.resolve({}),  
        } as unknown as Response)
      )//2.create user
        .mockImplementationOnce(() =>
        Promise.resolve(jsonResponse({}))
      );//set password

      await registerUser("newuser","new@example.com","pw123","New","User");
      expect(fetchSpy).toHaveBeenCalledTimes(3);
    expect(fetchSpy.mock.calls[1][0]).toBe(
      "http://localhost:8080/admin/realms/penflow/users"
    );
    expect(fetchSpy.mock.calls[2][0]).toBe(
      "http://localhost:8080/admin/realms/penflow/users/new-user-id/reset-password"
    );
  });

  it("throws a friendly error when the username/email already exists", async () => {
    jest
      .spyOn(global, "fetch")
      .mockImplementationOnce(() =>
        Promise.resolve(jsonResponse({ access_token: "adminToken" }))
      )
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({}, false, 409)));

    await expect(
      registerUser("dupe", "dupe@example.com", "pw123", "Dup", "User")
    ).rejects.toThrow("Username or email already exists");

});
});

*/