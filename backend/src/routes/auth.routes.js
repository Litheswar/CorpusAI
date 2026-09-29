import express from "express";

import { signupController, loginController, profileController } from "../controllers/auth.controller.js";
import { authenticate } from "../middleware/auth.middleware.js";

const router = express.Router();

router.post("/signup", signupController);
router.post("/login", loginController);


router.get("/me", authenticate, profileController);

export default router;