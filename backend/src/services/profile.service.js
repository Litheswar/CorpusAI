import { supabase } from "../config/supabase.js";

export async function getCurrentProfile() {
    const { data: { user }, error: userError } = await supabase.auth.getUser();

    if (userError) {
        throw new Error(userError.message);
    }

    if (!user) {
        throw new Error("User is not authenticated.");
    }

    const { data, error } = await supabase
        .from("profiles")
        .select(`
            id,
            full_name,
            role,
            company_id,
            companies (
                id,
                name
            )
        `)
        .eq("id", user.id)
        .single();

    if (error) {
        throw new Error(error.message);
    }

    return data;
}