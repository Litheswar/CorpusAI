import { supabase } from "../config/supabase.js";

export async function getCurrentProfile(userId) {
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
        .eq("id", userId)
        .single();

    if (error) {
        throw new Error(error.message);
    }

    return data;
}


export async function profileController(req, res) {
    try {
        const profile = await getCurrentProfile(req.user.id);

        res.status(200).json({
            profile
        });

    } catch (error) {
        res.status(500).json({
            error: error.message
        });
    }
}