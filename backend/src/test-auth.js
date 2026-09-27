import {
    login,
    getCurrentUser
} from "./services/auth.service.js";

import {
    getCurrentProfile
} from "./services/profile.service.js";

async function testAuth() {
    try {
        const loginData = await login({
            email: "testcompany@gmail.com", // <-- Update this to match your registered email
            password: "TestPassword123!"
        });

        console.log("✅ Login successful!");

        console.log("Session:");
        console.log(loginData.session);

        const user = await getCurrentUser();

        console.log("\n👤 Current User:");
        console.log(user.email);

        const profile = await getCurrentProfile();

        console.log("\n🏢 Current Profile:");
        console.log(profile);

    } catch (error) {
        console.error("❌ Error:");
        console.error(error.message);
    }
}

testAuth();