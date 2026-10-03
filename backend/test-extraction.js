import "dotenv/config";

import { supabase } from "./src/config/supabase.js";
import { extractText } from "./src/ai/document.loader.js";


const STORAGE_PATH = "PUT_YOUR_STORAGE_PATH_HERE";

const FILE_TYPE = "application/pdf";


async function test() {

    try {

        const text = await extractText({
            supabase,
            storagePath: STORAGE_PATH,
            fileType: FILE_TYPE
        });

        console.log("\n========== EXTRACTED TEXT ==========\n");

        console.log(text);

        console.log("\n========== END ==========\n");

    } catch (error) {

        console.error("Extraction failed:", error);

    }
}


test();