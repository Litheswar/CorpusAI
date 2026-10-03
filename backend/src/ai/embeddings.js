import { pipeline } from "@huggingface/transformers";

let embeddingPipeline = null;


async function getEmbeddingPipeline() {

    if (!embeddingPipeline) {

        console.log("Loading embedding model...");

        embeddingPipeline = await pipeline(
            "feature-extraction",
            "Xenova/all-MiniLM-L6-v2"
        );

        console.log("Embedding model loaded.");
    }

    return embeddingPipeline;
}


export async function generateEmbedding(text) {

    if (!text || !text.trim()) {
        throw new Error("Cannot generate embedding for empty text.");
    }

    const extractor = await getEmbeddingPipeline();

    const output = await extractor(text, {
        pooling: "mean",
        normalize: true
    });

    return Array.from(output.data);
}