import { createUserSupabaseClient } from "../config/supabase.js";

export async function authenticate(req, res, next) {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return res.status(401).json({
                error: "Authentication required."
            });
        }

        const token = authHeader.split(" ")[1];

        const userSupabase = createUserSupabaseClient(token);

        const {
            data: { user },
            error
        } = await userSupabase.auth.getUser();

        if (error || !user) {
            return res.status(401).json({
                error: "Invalid or expired token."
            });
        }

        req.user = user;
        req.supabase = userSupabase;

        next();

    } catch (error) {
        return res.status(401).json({
            error: "Authentication failed."
        });
    }
}