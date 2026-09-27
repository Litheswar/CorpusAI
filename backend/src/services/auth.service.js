import { supabase } from "../config/supabase.js";

export async function signUp({ email, password, fullName, companyName }) {
    const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
            data: {
                full_name: fullName,
                company_name: companyName
            }
        }
    });

    if (error) {
        throw new Error(error.message);
    }

    return data;
}



export async function login({ email, password }) {
    const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
    });

    if (error) {
        throw new Error(error.message);
    }

    return data;
}



export async function logout() {
    const { error } = await supabase.auth.signOut();

    if (error) {
        throw new Error(error.message);
    }
}



export async function getCurrentUser() {
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error) {
        throw new Error(error.message);
    }

    return user;
}