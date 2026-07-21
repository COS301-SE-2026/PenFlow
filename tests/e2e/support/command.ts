//reusable functions file

Cypress.Commands.add( "login" , (username: string, password:string) => {
    cy.visit("/login");
    cy.get('input[name="username"]').type(username);
    cy.get('input[name="password"]').type(password);
    cy.contains("button",/^LOG IN$/).click();
    cy.url().should("not.include","/login");
});


