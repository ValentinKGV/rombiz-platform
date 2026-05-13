import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        host: true,
        port: 3000,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
                ws: true,
                configure: (proxy) => {
                    proxy.on("error", (err) => {
                        if ((err as NodeJS.ErrnoException).code === "ECONNRESET") return;
                        console.error("[proxy]", err.message);
                    });
                },
            },
        },
    },
    build: {
        outDir: "dist",
        sourcemap: true,
    },
});
