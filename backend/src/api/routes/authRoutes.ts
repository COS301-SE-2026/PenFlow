import { Router } from "express";
import * as authController from "../controllers/authController";

const router: Router = Router();

// eslint-disable-next-line @typescript-eslint/no-misused-promises
router.post("/auth/register", authController.register);
// eslint-disable-next-line @typescript-eslint/no-misused-promises
router.post("/auth/login", authController.login);

export default router;
