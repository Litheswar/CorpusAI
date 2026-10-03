import "dotenv/config";

import { supabase } from "./config/supabase.js";
import { extractText } from "./ai/document.loader.js";
import { splitDocumentText } from "./ai/text.splitter.js";

const email = process.env.TEST_EMAIL;
const password = process.env.TEST_PASSWORD;

async function test() {
    if (!email || !password) {
        throw new Error("Set TEST_EMAIL and TEST_PASSWORD before running this test.");
    }

    try {
        const { data: auth, error: loginError } = await supabase.auth.signInWithPassword({
            email,
            password
        });
        if (loginError) throw new Error(`Login failed: ${loginError.message}`);

        const { data: profile, error: profileError } = await supabase
            .from("profiles")
            .select("company_id")
            .eq("id", auth.user.id)
            .single();
        if (profileError) throw new Error(`Profile lookup failed: ${profileError.message}`);
        if (!profile?.company_id) throw new Error("The signed-in user has no company.");

        const { data: documents, error: documentsError } = await supabase
            .from("documents")
            .select("name, storage_path, file_type")
            .eq("company_id", profile.company_id)
            .order("created_at", { ascending: false });
        if (documentsError) throw new Error(`Document lookup failed: ${documentsError.message}`);
        if (!documents?.length) throw new Error("No documents found for this company.");

        const document = documents[0];
        console.log(`Document selected: ${document.name}`);
        console.log(`Storage bucket: documents`);
        console.log(`Storage path: ${document.storage_path}`);
        console.log(`File type: ${document.file_type}`);

        const text = await extractText({
            supabase,
            storagePath: document.storage_path,
            fileType: document.file_type
        });
        console.log(`Extracted characters: ${text.length}`);

        const chunks = await splitDocumentText(text);
        console.log(`Chunk size setting: 1000; overlap setting: 200`);
        console.log(`Total chunks: ${chunks.length}`);
        chunks.forEach((chunk, index) => {
            const content = chunk.pageContent;
            const preview = content.replace(/\s+/g, " ").slice(0, 160);
            console.log(`Chunk ${index + 1}: ${content.length} characters; preview=${JSON.stringify(preview)}`);
        });

        console.log("Chunking test succeeded.");
    } finally {
        await supabase.auth.signOut();
    }
}

test().catch((error) => {
    console.error("Chunking failed:", error.message);
    process.exitCode = 1;
});
