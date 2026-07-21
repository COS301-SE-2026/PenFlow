//User login 
describe("User Login",()=>{
    it("User login and redirect to the dashboard",()=>{
        cy.login("1234","1234")

        //authenticated user and reach dashboard after it implemented
        // cy.url().should("include","/dashboard")
    });

}
);


