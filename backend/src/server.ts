import { env } from "./config/env";
import { initializeDatabase } from "./config/database";
import app from "./app";

initializeDatabase();

const PORT = env.PORT;

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`    - Local:       http://localhost:${PORT}`);
  // eslint-disable-next-line no-console
  console.log(`    - Docs:        http://localhost:${PORT}/api/docs`);
});