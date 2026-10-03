import { PDFParse } from "pdf-parse";
import mammoth from "mammoth";


export async function extractText({ supabase, storagePath, fileType }) {

    // 1. Download document from Supabase Storage
    const { data: fileData, error: downloadError } = await supabase.storage
        .from("documents")
        .download(storagePath);

    if (downloadError || !fileData) {
        throw new Error(
            `Failed to download document: ${
                downloadError?.message || "Unknown error"
            }`
        );
    }


    // 2. Convert Blob → Buffer
    const arrayBuffer = await fileData.arrayBuffer();

    const buffer = Buffer.from(arrayBuffer);


    // 3. Extract text based on file type

    // PDF
    if (fileType === "application/pdf") {
        const parser = new PDFParse({ data: buffer });

        try {
            const result = await parser.getText();
            return result.text.trim();
        } finally {
            await parser.destroy();
        }
    }


    // DOCX
    if (
        fileType ===
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ) {

        const result = await mammoth.extractRawText({
            buffer
        });

        return result.value.trim();
    }


    // TXT
    if (fileType === "text/plain") {

        return buffer.toString("utf-8").trim();
    }


    throw new Error("Unsupported document type.");
}
