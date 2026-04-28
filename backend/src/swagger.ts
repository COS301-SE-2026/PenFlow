import swaggerJsdoc from "swagger-jsdoc";

const options: swaggerJsdoc.Options = {
  definition: {
    openapi: "3.0.0",
    info: {
      title: "PenFlow API",
      version: "1.0.0",
      description: "API documentation for PenFlow penetration testing platform",
    },
    servers: [
      {
        url: "http://localhost:3001"
      },
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: "http",
          scheme: "bearer",
          bearerFormat: "JWT",
        },
      },
    },
  },
  apis: ["./src/api/routes/*.ts", "./src/api/controllers/*.ts"],
};

export const swaggerSpec = swaggerJsdoc(options);