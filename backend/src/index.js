import { supabase } from "./config/supabase.js";

async function testConnection() {
    const { data, error } = await supabase
        .from("companies")
        .select("id")
        .limit(1);

    if (error) {
        console.error("❌ Supabase connection failed:");
        console.error(error.message);
        return;
    }

    console.log("✅ Supabase connection successful!");
    console.log("Companies:", data);
}

testConnection();