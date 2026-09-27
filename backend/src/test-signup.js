import { signUp } from "./services/auth.service.js";

async function testSignup() {
    try {
        const data = await signUp({
            email: "testcompany@gmail.com",
            password: "TestPassword123!",
            fullName: "Test Owner",
            companyName: "Test Company"
        });

        console.log("✅ Signup successful!");
        console.log(data);
    } catch (error) {
        console.error("❌ Signup failed:");
        console.error(error.message);
    }
}

testSignup();