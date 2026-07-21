//set up
import "./command"

//avoid HMR/Dev server websocket drop
Cypress.on("uncaught:exception",(err)=>{
    if(err.message.includes("Connection closed")){
        return false;
    }
});

//