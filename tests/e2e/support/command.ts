//reusable functions file



Cypress.Commands.add( "login" , (username: string, password:string) => {
    cy.visit("/login");
    cy.get('input[name="username"]').type(username);
    cy.get('input[name="password"]').type(password);
    cy.contains("button",/^LOGIN$/).click();
    cy.url().should("not.include","/login");
    //logged_in cookie is not http only , for auth check
    cy.getCookie("logged_in").should("have.property","value","1")
});



declare global {
namespace Cypress{
        //cypress Chainable allow method chaining
    interface Chainable<Subject = any>{

        login(username: string , password :string):Chainable<void>;
    }
}


}

export {}
