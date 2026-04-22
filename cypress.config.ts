import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    specPattern: "tests/e2e/specs/**/*.cy.{js,jsx,ts,tsx}",
    supportFile: "tests/e2e/support/e2e.ts",
    screenshotsFolder: "tests/e2e/screenshots",
    videosFolder: "tests/e2e/videos",
  },
});