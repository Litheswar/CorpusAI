import { randomUUID } from "crypto";

const ALLOWED_FILE_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain"
];

export async function uploadDocument({
    supabase,
    userId,
    file
}) {
    // 1. Validate file
    if (!file) {
        throw new Error("No file provided.");
    }

    if (!ALLOWED_FILE_TYPES.includes(file.mimetype)) {
        throw new Error(
            "Unsupported file type. Only PDF, DOCX and TXT files are allowed."
        );
    }

    // 2. Get user's profile
    const {
        data: profile,
        error: profileError
    } = await supabase
        .from("profiles")
        .select("company_id")
        .eq("id", userId)
        .single();

    if (profileError || !profile) {
        throw new Error("User profile not found.");
    }

    if (!profile.company_id) {
        throw new Error("User is not associated with a company.");
    }

    const companyId = profile.company_id;

    // 3. Generate document ID
    const documentId = randomUUID();

    // 4. Get file extension
    const originalName = file.originalname;

    const extension = originalName.includes(".")
        ? originalName.split(".").pop().toLowerCase()
        : "";

    // 5. Create storage path
    const storagePath =
        `${companyId}/${documentId}.${extension}`;

    // 6. Upload file to Supabase Storage
    const {
        error: storageError
    } = await supabase.storage
        .from("documents")
        .upload(storagePath, file.buffer, {
            contentType: file.mimetype,
            upsert: false
        });

    if (storageError) {
        throw new Error(
            `File upload failed: ${storageError.message}`
        );
    }

    // 7. Save document metadata
    const {
        data: document,
        error: documentError
    } = await supabase
        .from("documents")
        .insert({
            id: documentId,
            company_id: companyId,
            uploaded_by: userId,
            name: originalName,
            storage_path: storagePath,
            file_type: file.mimetype,
            file_size: file.size
        })
        .select()
        .single();

    // 8. Cleanup storage if database insert fails
    if (documentError) {
        await supabase.storage
            .from("documents")
            .remove([storagePath]);

        throw new Error(
            `Document metadata creation failed: ${documentError.message}`
        );
    }

    return document;
}




export async function getCompanyDocuments({
    supabase,
    userId
}) {
    // Get user's company
    const {
        data: profile,
        error: profileError
    } = await supabase
        .from("profiles")
        .select("company_id")
        .eq("id", userId)
        .single();

    if (profileError || !profile) {
        throw new Error("User profile not found.");
    }

    if (!profile.company_id) {
        throw new Error("User is not associated with a company.");
    }

    // Get documents belonging to the user's company
    const {
        data: documents,
        error: documentsError
    } = await supabase
        .from("documents")
        .select(`
            id,
            name,
            storage_path,
            file_type,
            file_size,
            uploaded_by,
            created_at,
            updated_at
        `)
        .eq("company_id", profile.company_id)
        .order("created_at", {
            ascending: false
        });

    if (documentsError) {
        throw new Error(documentsError.message);
    }

    return documents;
}



export async function getDocumentDownloadUrl({
    supabase,
    userId,
    documentId
}) {
    // Get user's company
    const {
        data: profile,
        error: profileError
    } = await supabase
        .from("profiles")
        .select("company_id")
        .eq("id", userId)
        .single();

    if (profileError || !profile) {
        throw new Error("User profile not found.");
    }

    if (!profile.company_id) {
        throw new Error("User is not associated with a company.");
    }

    // Find the document
    const {
        data: document,
        error: documentError
    } = await supabase
        .from("documents")
        .select(`
            id,
            name,
            storage_path,
            file_type,
            file_size
        `)
        .eq("id", documentId)
        .eq("company_id", profile.company_id)
        .single();

    if (documentError || !document) {
        throw new Error("Document not found.");
    }

    // Generate a temporary signed URL
    const {
        data: signedUrlData,
        error: signedUrlError
    } = await supabase.storage
        .from("documents")
        .createSignedUrl(
            document.storage_path,
            60 * 5
        );

    if (signedUrlError) {
        throw new Error(
            `Could not generate download URL: ${signedUrlError.message}`
        );
    }

    return {
        id: document.id,
        name: document.name,
        file_type: document.file_type,
        file_size: document.file_size,
        download_url: signedUrlData.signedUrl
    };
}