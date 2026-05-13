import { useEffect, useRef, useState, useCallback } from "react";
import { wsClient } from "@/lib/websocket";
import type { Alert } from "@/types";

/**
 * Hook to subscribe to WebSocket alerts with lifecycle management.
 * Returns { isConnected, lastAlert, alerts }.
 */
export function useWebSocket(onAlert?: (alert: Alert) => void) {
    const [isConnected, setIsConnected] = useState(false);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const callbackRef = useRef(onAlert);
    callbackRef.current = onAlert;

    useEffect(() => {
        wsClient.connect();
        setIsConnected(true);

        const unsubscribe = wsClient.onAlert((alert) => {
            setAlerts((prev) => [alert, ...prev].slice(0, 50)); // Keep last 50
            callbackRef.current?.(alert);
        });

        return () => {
            unsubscribe();
        };
    }, []);

    const clearAlerts = useCallback(() => setAlerts([]), []);

    return { isConnected, alerts, clearAlerts };
}
