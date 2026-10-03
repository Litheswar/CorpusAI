import { generateEmbedding } from "./ai/embeddings.js";


async function test() {

    try {

        const text =
            "Employees are entitled to 12 days of casual leave.";

        const vector = await generateEmbedding(text);


        console.log("\n========== EMBEDDING ==========\n");

        console.log("Vector dimensions:", vector.length);

        console.log("First 10 values:");

        console.log(vector.slice(0, 10));

        console.log("\n========== END ==========\n");

    } catch (error) {

        console.error("Embedding generation failed:", error);
        process.exitCode = 1;

    }
}


test();
