import { signUp, login } from "../services/auth.service.js";
import { getCurrentProfile } from "../services/profile.service.js";

export async function signupController(req, res) {
    try {
        const { email, password, fullName, companyName } = req.body;

        if (!email || !password || !fullName || !companyName) {
            return res.status(400).json({
                error: "All fields are required."
            });
        }

        const data = await signUp({ email, password, fullName, companyName });

        res.status(201).json({
            message: "Signup successful",
            user: data.user,
            session: data.session
        });

    } 
    catch (error) {
        res.status(400).json({
            error: error.message
        });
    }
}

export async function loginController(req, res) {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({
                error: "Email and password are required."
            });
        }

        const data = await login({
            email,
            password
        });

        res.status(200).json({
            message: "Login successful",
            user: data.user,
            session: data.session
        });

    } 
    catch (error) {
        res.status(401).json({
            error: error.message
        });
    }
}


export async function profileController(req, res) {
    try {
        const profile = await getCurrentProfile();

        res.status(200).json({
            profile
        });

    } 
    catch (error) {
        res.status(500).json({
            error: error.message
        });
    }
}