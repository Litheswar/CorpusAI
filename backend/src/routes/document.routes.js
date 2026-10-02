import express from "express";
import multer from "multer";

import { authenticate } from "../middleware/auth.middleware.js";
import { uploadDocumentController, getDocumentsController, getDocumentDownloadController, deleteDocumentController } from "../controllers/document.controller.js";

const router = express.Router();

const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: 10 * 1024 * 1024
    }
});

router.post(
    "/upload",
    authenticate,
    upload.single("file"),
    uploadDocumentController
);


router.get(
    "/",
    authenticate,
    getDocumentsController
);

router.get(
    "/:id/download",
    authenticate,
    getDocumentDownloadController
);

router.delete(
    "/:id",
    authenticate,
    deleteDocumentController
);

export default router;