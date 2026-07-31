//delete domain remove a domain from the detail panel
describe('Delete Domain', () => {
    beforeEach(() => {
      cy.login("1234", "1234");
      cy.visit("/domains");
    });
    //delete domain
    it("adds a new domain then delete it",() =>{
        const domain = `e2e-test-${Date.now()}.example.com`;
        
        cy.get('button[aria-pressed]').contains("Add Domain").click();
        cy.get("#new-domain").type(domain);
        cy.contains("button", "Cancel").parent().contains("button", "Add Domain").click();
        cy.contains("td", domain).should("be.visible");
        cy.contains("td", domain).click();
        cy.contains("button", "Remove domain").click();

        cy.contains("td", domain).should("not.exist");
    
    })
})
