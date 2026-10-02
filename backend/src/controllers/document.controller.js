import { uploadDocument, getCompanyDocuments, getDocumentDownloadUrl, deleteDocument } from "../services/document.service.js";

export async function uploadDocumentController(req, res) {
    try {
        const document = await uploadDocument({
            supabase: req.supabase,
            userId: req.user.id,
            file: req.file
        });

        res.status(201).json({
            message: "Document uploaded successfully.",
            document
        });

    } catch (error) {
        res.status(400).json({
            error: error.message
        });
    }
}


export async function getDocumentsController(req, res) {
    try {
        const documents = await getCompanyDocuments({
            supabase: req.supabase,
            userId: req.user.id
        });

        res.status(200).json({
            documents
        });

    } catch (error) {
        res.status(500).json({
            error: error.message
        });
    }
}



export async function getDocumentDownloadController(req, res) {
    try {
        const document = await getDocumentDownloadUrl({
            supabase: req.supabase,
            userId: req.user.id,
            documentId: req.params.id
        });

        res.status(200).json({
            document
        });

    } catch (error) {
        res.status(404).json({
            error: error.message
        });
    }
}


export async function deleteDocumentController(req, res) {

    try {

        const result = await deleteDocument({
            supabase: req.supabase,
            userId: req.user.id,
            documentId: req.params.id
        });

        res.status(200).json({
            message: "Document deleted successfully.",
            result
        });

    } catch (error) {

        res.status(404).json({
            error: error.message
        });

    }
}