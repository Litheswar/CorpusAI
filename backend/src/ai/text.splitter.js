import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";

import { AI_CONFIG } from "./config.js";


const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: AI_CONFIG.chunkSize,
    chunkOverlap: AI_CONFIG.chunkOverlap,
});


export async function splitDocumentText(text) {

    if (!text || !text.trim()) {
        throw new Error("Document contains no extractable text.");
    }

    const chunks = await splitter.createDocuments([text]);

    return chunks;
}
