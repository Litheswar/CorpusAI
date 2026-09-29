import express  from "express";
import cors from "cors";

import authRoutes from "./routes/auth.routes.js";

const app = express();

const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json())

app.get("/", (req, res) => {
    res.json({
        message: "CompanyBrain backend is running 🚀"
    });
});

app.use("/api/auth", authRoutes)

app.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
});