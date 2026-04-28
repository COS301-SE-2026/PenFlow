import express, { Express } from "express";
import cors from "cors";
import swaggerUi from "swagger-ui-express";

import scanRoutes from "./api/routes/scanRoutes";
import authRoutes from "./api/routes/authRoutes";
import { swaggerSpec } from "./swagger";

const app: Express = express();

app.use(
  cors({
    origin: process.env.CORS_ORIGIN || "http://localhost:3000",
    credentials: true
  })
);

app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.use("/api/docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec));

app.use("/api", scanRoutes);
app.use("/api", authRoutes);

export default app;