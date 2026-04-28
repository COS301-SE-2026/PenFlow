import { Router } from "express";
import * as scanController from "../controllers/scanController";

const router: Router = Router();

// eslint-disable-next-line @typescript-eslint/no-misused-promises
router.get("/scans", scanController.listScans);
// eslint-disable-next-line @typescript-eslint/no-misused-promises
router.post("/scans", scanController.createScan);
// eslint-disable-next-line @typescript-eslint/no-misused-promises
router.get("/scans/:id", scanController.getScanById);

export default router;
