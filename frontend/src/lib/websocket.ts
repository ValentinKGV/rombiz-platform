/**
 * WebSocket client for real-time alerts.
 */
import type { Alert } from "@/types";

type AlertHandler = (alert: Alert) => void;

class WebSocketClient {
    private ws: WebSocket | null = null;
    private handlers: AlertHandler[] = [];
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;

    connect() {
        const token = localStorage.getItem("access_token");
        if (!token) return;

        const wsBase = import.meta.env.VITE_WS_URL ||
            window.location.origin.replace(/^http/, "ws");

        this.ws = new WebSocket(`${wsBase}/api/v1/alerts/ws/${token}`);

        this.ws.onopen = () => {
            console.log("[WS] Connected");
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            try {
                const alert: Alert = JSON.parse(event.data);
                this.handlers.forEach((handler) => handler(alert));
            } catch (e) {
                console.error("[WS] Parse error:", e);
            }
        };

        this.ws.onclose = () => {
            console.log("[WS] Disconnected");
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error("[WS] Error:", error);
        };
    }

    private attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        setTimeout(() => {
            console.log(`[WS] Reconnect attempt ${this.reconnectAttempts}...`);
            this.connect();
        }, delay);
    }

    onAlert(handler: AlertHandler) {
        this.handlers.push(handler);
        return () => {
            this.handlers = this.handlers.filter((h) => h !== handler);
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

export const wsClient = new WebSocketClient();
