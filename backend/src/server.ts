import { env } from "./config/env";
import { initializeDatabase } from "./config/database";
import app from "./app";

initializeDatabase();

const PORT = env.PORT;

app.listen(PORT, () => {
  console.log(`    - Local:       http://localhost:${PORT}`);
  console.log(`    - Docs:        http://localhost:${PORT}/api/docs`);
});