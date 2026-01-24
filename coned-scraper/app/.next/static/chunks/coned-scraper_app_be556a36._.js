(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/coned-scraper/app/components/Dashboard.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>Dashboard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
'use client';
;
const API_BASE_URL = __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL || '/api';
function Dashboard() {
    _s();
    const [isRunning, setIsRunning] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [logs, setLogs] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [status, setStatus] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('stopped');
    const logContainerRef = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const [apiError, setApiError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [previewUrl, setPreviewUrl] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const previewRefreshIntervalRef = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(null);
    const loadLogs = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Dashboard.useCallback[loadLogs]": async ()=>{
            try {
                let response = null;
                try {
                    response = await fetch("".concat(API_BASE_URL, "/logs?limit=100"), {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                } catch (fetchError) {
                    // Network error - service might not be running
                    console.error('Network error loading logs:', fetchError);
                    // Don't set error state for logs, just keep existing logs
                    return;
                }
                if (response && response.ok) {
                    try {
                        const data = await response.json();
                        setLogs((data.logs || []).reverse()); // Show newest at bottom
                    } catch (jsonError) {
                        console.error('Failed to parse logs JSON:', jsonError);
                        setLogs([]);
                    }
                } else if (response) {
                    // HTTP error response
                    console.error('Failed to load logs:', response.status, response.statusText);
                }
            // If response is null (network error), keep existing logs
            } catch (error) {
                console.error('Failed to load logs:', error);
            // Keep existing logs on error
            }
        }
    }["Dashboard.useCallback[loadLogs]"], []);
    const loadLivePreview = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Dashboard.useCallback[loadLivePreview]": async ()=>{
            try {
                var _response_headers_get;
                const timestamp = new Date().getTime();
                const url = "".concat(API_BASE_URL, "/live-preview?t=").concat(timestamp);
                const response = await fetch(url);
                if (response.ok && ((_response_headers_get = response.headers.get('content-type')) === null || _response_headers_get === void 0 ? void 0 : _response_headers_get.startsWith('image/'))) {
                    const blob = await response.blob();
                    const imageUrl = URL.createObjectURL(blob);
                    // Revoke old URL to prevent memory leaks
                    setPreviewUrl({
                        "Dashboard.useCallback[loadLivePreview]": (prevUrl)=>{
                            if (prevUrl && prevUrl.startsWith('blob:')) {
                                URL.revokeObjectURL(prevUrl);
                            }
                            return imageUrl;
                        }
                    }["Dashboard.useCallback[loadLivePreview]"]);
                } else {
                    // Preview not available yet (404 or other error)
                    setPreviewUrl({
                        "Dashboard.useCallback[loadLivePreview]": (prevUrl)=>{
                            if (prevUrl && prevUrl.startsWith('blob:')) {
                                URL.revokeObjectURL(prevUrl);
                            }
                            return null;
                        }
                    }["Dashboard.useCallback[loadLivePreview]"]);
                }
            } catch (error) {
                // Silently fail - preview might not be available
                setPreviewUrl({
                    "Dashboard.useCallback[loadLivePreview]": (prevUrl)=>{
                        if (prevUrl && prevUrl.startsWith('blob:')) {
                            URL.revokeObjectURL(prevUrl);
                        }
                        return null;
                    }
                }["Dashboard.useCallback[loadLivePreview]"]);
            }
        }
    }["Dashboard.useCallback[loadLivePreview]"], []);
    const loadScrapedData = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "Dashboard.useCallback[loadScrapedData]": async ()=>{
        // Removed - scraped data is now in AccountLedger component
        }
    }["Dashboard.useCallback[loadScrapedData]"], []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Dashboard.useEffect": ()=>{
            loadLogs();
            loadLivePreview();
            // Refresh logs every 1 second for faster updates
            const logInterval = setInterval(loadLogs, 1000);
            // Refresh preview every 500ms when running, 2s when stopped
            const previewInterval = setInterval(loadLivePreview, isRunning ? 500 : 2000);
            previewRefreshIntervalRef.current = previewInterval;
            return ({
                "Dashboard.useEffect": ()=>{
                    clearInterval(logInterval);
                    if (previewRefreshIntervalRef.current) {
                        clearInterval(previewRefreshIntervalRef.current);
                    }
                }
            })["Dashboard.useEffect"];
        }
    }["Dashboard.useEffect"], [
        loadLogs,
        loadLivePreview,
        isRunning
    ]);
    // Cleanup blob URL on unmount
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Dashboard.useEffect": ()=>{
            return ({
                "Dashboard.useEffect": ()=>{
                    if (previewUrl && previewUrl.startsWith('blob:')) {
                        URL.revokeObjectURL(previewUrl);
                    }
                }
            })["Dashboard.useEffect"];
        }
    }["Dashboard.useEffect"], [
        previewUrl
    ]);
    // Auto-scroll logs to bottom when new logs are added
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Dashboard.useEffect": ()=>{
            if (logContainerRef.current) {
                logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
            }
        }
    }["Dashboard.useEffect"], [
        logs
    ]);
    const handleStartScraper = async ()=>{
        setIsRunning(true);
        setStatus('running');
        // Clear logs when starting a new scrape
        setLogs([]);
        try {
            // Clear logs on the backend as well
            await fetch("".concat(API_BASE_URL, "/logs"), {
                method: 'DELETE'
            }).catch(()=>{
            // Ignore errors if endpoint doesn't exist or fails
            });
            // Use safeFetch helper to handle network errors
            const safeFetch = async (url, options)=>{
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(()=>controller.abort(), 30000) // 30 second timeout
                    ;
                    const response = await fetch(url, {
                        ...options,
                        signal: controller.signal
                    });
                    clearTimeout(timeoutId);
                    return response;
                } catch (error) {
                    // Silently catch network errors
                    return null;
                }
            };
            const response = await safeFetch("".concat(API_BASE_URL, "/scrape"), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (response && response.ok) {
                const result = await response.json();
                setStatus(result.success ? 'stopped' : 'error');
                // Refresh logs after scraping
                setTimeout(()=>{
                    loadLogs();
                }, 1000);
            } else if (response) {
                // HTTP error response
                let errorMessage = 'Unknown error occurred';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorData.error || errorData.message || 'Unknown error occurred';
                } catch (e) {
                    // If response is not JSON, try to get text
                    try {
                        const text = await response.text();
                        errorMessage = text || "HTTP ".concat(response.status, ": ").concat(response.statusText);
                    } catch (e) {
                        errorMessage = "HTTP ".concat(response.status, ": ").concat(response.statusText);
                    }
                }
                setStatus('error');
                setApiError("Scraper error: ".concat(errorMessage));
                console.error('Scraper error:', errorMessage);
            } else {
                // No response (network error)
                setStatus('error');
                setApiError('Cannot connect to Python service. Make sure it\'s running on port 8000.');
            // Don't log to console - error is already shown to user via setApiError
            }
        } catch (error) {
            setStatus('error');
            setApiError('Failed to start scraper. Check console for details.');
            console.error('Failed to start scraper:', error);
        } finally{
            setIsRunning(false);
        }
    };
    const formatTimestamp = (timestamp)=>{
        try {
            const date = new Date(timestamp);
            const dateStr = date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
            const timeStr = date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
            return {
                date: dateStr,
                time: timeStr
            };
        } catch (e) {
            return {
                date: timestamp,
                time: ''
            };
        }
    };
    const formatTimestampForLogs = (timestamp)=>{
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch (e) {
            return timestamp;
        }
    };
    const getLogLevelClass = (level)=>{
        switch(level.toLowerCase()){
            case 'error':
                return 'log-level-error';
            case 'success':
                return 'log-level-success';
            case 'warning':
                return 'log-level-warning';
            default:
                return 'log-level-info';
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "ha-dashboard",
        children: [
            apiError && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card ha-card-error",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-header",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "ha-card-icon",
                                children: "⚠️"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 263,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                children: "API Connection Error"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 264,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                        lineNumber: 262,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-content",
                        children: apiError
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                        lineNumber: 266,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                lineNumber: 261,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card ha-card-status",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-header",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "ha-card-icon",
                                children: "🔌"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 272,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                children: "Service Status"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 273,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                        lineNumber: 271,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-content",
                        style: {
                            padding: '0.5rem 0.75rem'
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-status-controls",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "ha-status-info",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "ha-status-indicator ".concat(status)
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                            lineNumber: 278,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "ha-status-text",
                                            children: status === 'running' ? 'Running' : status === 'error' ? 'Error' : 'Stopped'
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                            lineNumber: 279,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                    lineNumber: 277,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    className: "ha-button ha-button-primary",
                                    onClick: handleStartScraper,
                                    disabled: isRunning,
                                    children: isRunning ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                                                src: "/images/ajax-loader.gif",
                                                alt: "Loading",
                                                className: "ha-loader-inline"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                                lineNumber: 290,
                                                columnNumber: 19
                                            }, this),
                                            "Running..."
                                        ]
                                    }, void 0, true) : 'Start Scraper'
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                    lineNumber: 283,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                            lineNumber: 276,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                        lineNumber: 275,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                lineNumber: 270,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                style: {
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '1rem',
                    height: '100%'
                },
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card ha-card-logs",
                        style: {
                            display: 'flex',
                            flexDirection: 'column',
                            minHeight: 0
                        },
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-card-header",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "ha-card-icon",
                                        children: "📝"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                        lineNumber: 304,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        children: "Console Logs"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                        lineNumber: 305,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 303,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-card-content ha-log-container",
                                ref: logContainerRef,
                                style: {
                                    flex: 1,
                                    minHeight: 0,
                                    overflowY: 'auto'
                                },
                                children: logs.length === 0 ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "ha-empty-state",
                                    children: "No logs yet. Start the scraper to see activity."
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                    lineNumber: 309,
                                    columnNumber: 15
                                }, this) : logs.map((log)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "ha-log-entry ha-log-".concat(log.level.toLowerCase()),
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "ha-log-time",
                                                children: formatTimestampForLogs(log.timestamp)
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                                lineNumber: 313,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: getLogLevelClass(log.level),
                                                children: [
                                                    "[",
                                                    log.level.toUpperCase(),
                                                    "]"
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                                lineNumber: 314,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "ha-log-message",
                                                children: log.message
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                                lineNumber: 315,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, log.id, true, {
                                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                        lineNumber: 312,
                                        columnNumber: 17
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 307,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                        lineNumber: 302,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card",
                        style: {
                            display: 'flex',
                            flexDirection: 'column',
                            minHeight: 0
                        },
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-card-header",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "ha-card-icon",
                                        children: "🖥️"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                        lineNumber: 324,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        children: "Browser Preview"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                        lineNumber: 325,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 323,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-card-content",
                                style: {
                                    flex: 1,
                                    minHeight: 0,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    backgroundColor: '#1a1a1a',
                                    padding: '1rem'
                                },
                                children: previewUrl ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                                    src: previewUrl,
                                    alt: "Browser preview",
                                    style: {
                                        maxWidth: '100%',
                                        maxHeight: '100%',
                                        objectFit: 'contain',
                                        border: '1px solid #333',
                                        borderRadius: '4px'
                                    }
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                    lineNumber: 329,
                                    columnNumber: 15
                                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "ha-empty-state",
                                    style: {
                                        textAlign: 'center',
                                        color: '#888'
                                    },
                                    children: isRunning ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                                                src: "/images/ajax-loader.gif",
                                                alt: "Loading",
                                                style: {
                                                    width: '40px',
                                                    height: '40px',
                                                    marginBottom: '1rem'
                                                }
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                                lineNumber: 344,
                                                columnNumber: 21
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                children: "Waiting for browser preview..."
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                                lineNumber: 349,
                                                columnNumber: 21
                                            }, this)
                                        ]
                                    }, void 0, true) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        children: "No preview available. Start the scraper to see browser activity."
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                        lineNumber: 352,
                                        columnNumber: 19
                                    }, this)
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                    lineNumber: 341,
                                    columnNumber: 15
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                                lineNumber: 327,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                        lineNumber: 322,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
                lineNumber: 301,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/coned-scraper/app/components/Dashboard.tsx",
        lineNumber: 259,
        columnNumber: 5
    }, this);
}
_s(Dashboard, "56rAekhOF5gLr47bjtrgzBx4qJ4=");
_c = Dashboard;
var _c;
__turbopack_context__.k.register(_c, "Dashboard");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/coned-scraper/app/components/Settings.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>Settings
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature(), _s2 = __turbopack_context__.k.signature();
'use client';
;
const API_BASE_URL = __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL || '/api';
function Settings() {
    _s();
    const [username, setUsername] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [password, setPassword] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [totpSecret, setTotpSecret] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [currentTOTP, setCurrentTOTP] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [timeRemaining, setTimeRemaining] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(30);
    const [isLoading, setIsLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [message, setMessage] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [activeTab, setActiveTab] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('credentials');
    // Show/hide password states
    const [showUsername, setShowUsername] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [showPassword, setShowPassword] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [showTotpSecret, setShowTotpSecret] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    // Helper function to mask text
    const maskText = (text)=>{
        if (!text) return '';
        return '•'.repeat(text.length);
    };
    // Load saved credentials on mount
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Settings.useEffect": ()=>{
            loadSettings();
        }
    }["Settings.useEffect"], []);
    // Update TOTP code every second
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "Settings.useEffect": ()=>{
            if (!totpSecret || totpSecret.trim() === '') {
                setCurrentTOTP('');
                setTimeRemaining(30);
                return;
            }
            const updateTOTP = {
                "Settings.useEffect.updateTOTP": async ()=>{
                    try {
                        const response = await fetch("".concat(API_BASE_URL, "/totp"));
                        if (response.ok) {
                            const data = await response.json();
                            setCurrentTOTP(data.code);
                            setTimeRemaining(data.time_remaining);
                        } else {
                            // Handle different error status codes
                            let errorMessage = 'Error';
                            try {
                                const errorData = await response.json();
                                if (response.status === 404) {
                                    errorMessage = 'No credentials saved';
                                } else if (response.status === 400) {
                                    errorMessage = errorData.detail || 'Invalid TOTP secret';
                                } else {
                                    errorMessage = errorData.detail || 'Failed to fetch TOTP';
                                }
                            } catch (e) {
                                // If response is not JSON, use status text
                                errorMessage = response.status === 404 ? 'No credentials saved' : 'Error';
                            }
                            setCurrentTOTP(errorMessage);
                        }
                    } catch (error) {
                        console.error('Failed to fetch TOTP:', error);
                        setCurrentTOTP('Connection Error');
                    }
                }
            }["Settings.useEffect.updateTOTP"];
            // Initial fetch immediately
            updateTOTP();
            // Update every second
            const interval = setInterval(updateTOTP, 1000);
            return ({
                "Settings.useEffect": ()=>clearInterval(interval)
            })["Settings.useEffect"];
        }
    }["Settings.useEffect"], [
        totpSecret
    ]);
    const loadSettings = async ()=>{
        try {
            const response = await fetch("".concat(API_BASE_URL, "/settings"));
            if (response.ok) {
                const data = await response.json();
                setUsername(data.username || '');
                setPassword(''); // Don't show saved password
                setTotpSecret(data.totp_secret || '');
                // Reset show states when loading
                setShowUsername(false);
                setShowPassword(false);
                setShowTotpSecret(false);
            // If TOTP secret exists, trigger TOTP fetch immediately
            // Note: The useEffect will handle TOTP updates automatically
            // so we don't need to fetch here
            } else {
                console.error('Failed to load settings:', await response.text());
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
            setMessage({
                type: 'error',
                text: 'Failed to connect to API. Make sure the Python service is running on port 8000.'
            });
        }
    };
    const handleSave = async (e)=>{
        e.preventDefault();
        setIsLoading(true);
        setMessage(null);
        try {
            const response = await fetch("".concat(API_BASE_URL, "/settings"), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    password: password || null,
                    totp_secret: totpSecret
                })
            });
            if (response.ok) {
                setMessage({
                    type: 'success',
                    text: 'Settings saved successfully!'
                });
                // Reload to get updated TOTP
                if (totpSecret) {
                    const totpResponse = await fetch("".concat(API_BASE_URL, "/totp"));
                    if (totpResponse.ok) {
                        const totpData = await totpResponse.json();
                        setCurrentTOTP(totpData.code);
                        setTimeRemaining(totpData.time_remaining);
                    }
                }
            } else {
                const error = await response.json();
                setMessage({
                    type: 'error',
                    text: error.detail || 'Failed to save settings'
                });
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: 'Failed to connect to API. Make sure the Python service is running.'
            });
        } finally{
            setIsLoading(false);
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "ha-settings",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-tabs",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        type: "button",
                        className: "ha-tab ".concat(activeTab === 'credentials' ? 'active' : ''),
                        onClick: ()=>setActiveTab('credentials'),
                        children: "🔐 Credentials"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 162,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        type: "button",
                        className: "ha-tab ".concat(activeTab === 'automated' ? 'active' : ''),
                        onClick: ()=>setActiveTab('automated'),
                        children: "⏰ Automated Scrape"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 169,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        type: "button",
                        className: "ha-tab ".concat(activeTab === 'webhooks' ? 'active' : ''),
                        onClick: ()=>setActiveTab('webhooks'),
                        children: "🔗 Home Assistant Webhooks"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 176,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 161,
                columnNumber: 7
            }, this),
            activeTab === 'credentials' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-header",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "ha-card-icon",
                                children: "🔐"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 188,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                children: "Credentials"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 189,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 187,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-content",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                                onSubmit: handleSave,
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "ha-form-group",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                htmlFor: "username",
                                                className: "ha-form-label",
                                                children: "Username / Email"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 194,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "password-input-wrapper",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                        type: showUsername ? "text" : "password",
                                                        id: "username",
                                                        className: "ha-form-input",
                                                        value: showUsername ? username : username ? maskText(username) : '',
                                                        onChange: (e)=>setUsername(e.target.value),
                                                        onFocus: ()=>setShowUsername(true),
                                                        placeholder: "your.email@example.com",
                                                        required: true
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                        lineNumber: 196,
                                                        columnNumber: 19
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                        type: "button",
                                                        className: "toggle-password",
                                                        onClick: ()=>setShowUsername(!showUsername),
                                                        tabIndex: -1,
                                                        "aria-label": showUsername ? "Hide username" : "Show username",
                                                        children: showUsername ? '👁️' : '👁️‍🗨️'
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                        lineNumber: 206,
                                                        columnNumber: 19
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 195,
                                                columnNumber: 17
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 193,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "ha-form-group",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                htmlFor: "password",
                                                className: "ha-form-label",
                                                children: "Password"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 219,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "password-input-wrapper",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                        type: showPassword ? "text" : "password",
                                                        id: "password",
                                                        className: "ha-form-input",
                                                        value: showPassword ? password : password ? maskText(password) : '',
                                                        onChange: (e)=>setPassword(e.target.value),
                                                        onFocus: ()=>setShowPassword(true),
                                                        placeholder: password ? '' : 'Enter password to update'
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                        lineNumber: 221,
                                                        columnNumber: 19
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                        type: "button",
                                                        className: "toggle-password",
                                                        onClick: ()=>setShowPassword(!showPassword),
                                                        tabIndex: -1,
                                                        "aria-label": showPassword ? "Hide password" : "Show password",
                                                        children: showPassword ? '👁️' : '👁️‍🗨️'
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                        lineNumber: 230,
                                                        columnNumber: 19
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 220,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "info-text",
                                                children: "Leave empty to keep existing password"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 240,
                                                columnNumber: 17
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 218,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "ha-form-group",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                htmlFor: "totp_secret",
                                                className: "ha-form-label",
                                                children: "TOTP Secret"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 246,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "password-input-wrapper",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                        type: showTotpSecret ? "text" : "password",
                                                        id: "totp_secret",
                                                        className: "ha-form-input",
                                                        value: showTotpSecret ? totpSecret : totpSecret ? maskText(totpSecret) : '',
                                                        onChange: (e)=>setTotpSecret(e.target.value),
                                                        onFocus: ()=>setShowTotpSecret(true),
                                                        placeholder: "JBSWY3DPEHPK3PXP",
                                                        required: true
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                        lineNumber: 248,
                                                        columnNumber: 19
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                        type: "button",
                                                        className: "toggle-password",
                                                        onClick: ()=>setShowTotpSecret(!showTotpSecret),
                                                        tabIndex: -1,
                                                        "aria-label": showTotpSecret ? "Hide TOTP secret" : "Show TOTP secret",
                                                        children: showTotpSecret ? '👁️' : '👁️‍🗨️'
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                        lineNumber: 258,
                                                        columnNumber: 19
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 247,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "info-text",
                                                children: "Enter your TOTP secret (base32 encoded string, same as Google Authenticator)"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 268,
                                                columnNumber: 17
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 245,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        type: "submit",
                                        className: "ha-button ha-button-primary",
                                        disabled: isLoading,
                                        children: isLoading ? 'Saving...' : 'Save Settings'
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 273,
                                        columnNumber: 15
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 192,
                                columnNumber: 13
                            }, this),
                            totpSecret && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-totp-display",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                        children: "Current TOTP Code"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 280,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "ha-totp-code",
                                        children: currentTOTP || 'Loading...'
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 281,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "ha-totp-time",
                                        children: [
                                            "Expires in ",
                                            timeRemaining,
                                            " seconds"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 282,
                                        columnNumber: 17
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 279,
                                columnNumber: 15
                            }, this),
                            message && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-card ha-card-".concat(message.type === 'error' ? 'error' : 'status'),
                                style: {
                                    marginTop: '1rem'
                                },
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "ha-card-content",
                                    children: message.text
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 290,
                                    columnNumber: 17
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 289,
                                columnNumber: 15
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 191,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 186,
                columnNumber: 9
            }, this),
            activeTab === 'automated' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(AutomatedScrapeTab, {}, void 0, false, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 300,
                columnNumber: 9
            }, this),
            activeTab === 'webhooks' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(WebhooksTab, {}, void 0, false, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 304,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
        lineNumber: 160,
        columnNumber: 5
    }, this);
}
_s(Settings, "MAbznaf6y9Vbn+IzXjz2RViWUls=");
_c = Settings;
function WebhooksTab() {
    _s1();
    const [latestBillUrl, setLatestBillUrl] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [previousBillUrl, setPreviousBillUrl] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [accountBalanceUrl, setAccountBalanceUrl] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [lastPaymentUrl, setLastPaymentUrl] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [isLoading, setIsLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [message, setMessage] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "WebhooksTab.useEffect": ()=>{
            loadWebhooks();
        }
    }["WebhooksTab.useEffect"], []);
    const loadWebhooks = async ()=>{
        try {
            const response = await fetch("".concat(API_BASE_URL, "/webhooks"));
            if (response.ok) {
                const data = await response.json();
                setLatestBillUrl(data.latest_bill || '');
                setPreviousBillUrl(data.previous_bill || '');
                setAccountBalanceUrl(data.account_balance || '');
                setLastPaymentUrl(data.last_payment || '');
            }
        } catch (error) {
            console.error('Failed to load webhooks:', error);
        }
    };
    const handleSave = async (e)=>{
        e.preventDefault();
        setIsLoading(true);
        setMessage(null);
        try {
            const payload = {
                latest_bill: latestBillUrl.trim(),
                previous_bill: previousBillUrl.trim(),
                account_balance: accountBalanceUrl.trim(),
                last_payment: lastPaymentUrl.trim()
            };
            const response = await fetch("".concat(API_BASE_URL, "/webhooks"), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (response.ok) {
                const data = await response.json();
                setMessage({
                    type: 'success',
                    text: "Webhook URLs saved successfully! (".concat(data.configured_count, " configured)")
                });
                await loadWebhooks();
            } else {
                let errorMessage = 'Failed to save webhook URLs';
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        if (typeof errorData.detail === 'string') {
                            errorMessage = errorData.detail;
                        } else if (Array.isArray(errorData.detail)) {
                            // Pydantic validation errors
                            errorMessage = errorData.detail.map((err)=>"".concat(err.loc.join('.'), ": ").concat(err.msg)).join(', ');
                        }
                    }
                } catch (e) {
                    errorMessage = "HTTP ".concat(response.status, ": ").concat(response.statusText);
                }
                setMessage({
                    type: 'error',
                    text: errorMessage
                });
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: "Failed to connect to API: ".concat(error instanceof Error ? error.message : 'Unknown error')
            });
        } finally{
            setIsLoading(false);
        }
    };
    const handleTest = async ()=>{
        setIsLoading(true);
        setMessage(null);
        try {
            // First, make sure webhooks are saved
            const saveResponse = await fetch("".concat(API_BASE_URL, "/webhooks"), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    latest_bill: latestBillUrl,
                    previous_bill: previousBillUrl,
                    account_balance: accountBalanceUrl,
                    last_payment: lastPaymentUrl
                })
            });
            if (!saveResponse.ok) {
                const errorData = await saveResponse.json().catch(()=>({}));
                setMessage({
                    type: 'error',
                    text: errorData.detail || 'Failed to save webhooks before testing'
                });
                setIsLoading(false);
                return;
            }
            // Test webhooks with existing data
            setMessage({
                type: 'success',
                text: 'Sending test webhooks with latest scraped data...'
            });
            const testResponse = await fetch("".concat(API_BASE_URL, "/webhooks/test"), {
                method: 'POST'
            });
            if (testResponse.ok) {
                const data = await testResponse.json();
                setMessage({
                    type: 'success',
                    text: "".concat(data.message).concat(data.webhooks_sent ? " (".concat(data.webhooks_sent.join(', '), ")") : '')
                });
            } else {
                const errorData = await testResponse.json().catch(()=>({}));
                setMessage({
                    type: 'error',
                    text: errorData.detail || 'Test webhooks failed'
                });
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: 'Failed to test webhooks. Make sure the Python service is running.'
            });
        } finally{
            setIsLoading(false);
        }
    };
    const hasAnyWebhook = latestBillUrl.trim() || previousBillUrl.trim() || accountBalanceUrl.trim() || lastPaymentUrl.trim();
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "ha-card",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card-header",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "ha-card-icon",
                        children: "🔗"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 443,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        children: "Home Assistant Webhooks"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 444,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 442,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card-content",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "info-text",
                        style: {
                            marginBottom: '1.5rem'
                        },
                        children: "Configure separate webhook URLs for each event type. Each scrape will POST JSON data to the configured URLs."
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 447,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                        onSubmit: handleSave,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-form-group",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                        htmlFor: "latest-bill-url",
                                        className: "ha-form-label",
                                        children: "📄 Latest Bill Webhook"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 453,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        type: "url",
                                        id: "latest-bill-url",
                                        className: "ha-form-input",
                                        value: latestBillUrl,
                                        onChange: (e)=>setLatestBillUrl(e.target.value),
                                        placeholder: "https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID",
                                        style: {
                                            fontFamily: 'monospace',
                                            fontSize: '0.9rem'
                                        }
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 456,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "info-text",
                                        children: "Sends latest bill amount, billing cycle date, and month range"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 465,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 452,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-form-group",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                        htmlFor: "previous-bill-url",
                                        className: "ha-form-label",
                                        children: "📋 Previous Bill Webhook"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 471,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        type: "url",
                                        id: "previous-bill-url",
                                        className: "ha-form-input",
                                        value: previousBillUrl,
                                        onChange: (e)=>setPreviousBillUrl(e.target.value),
                                        placeholder: "https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID",
                                        style: {
                                            fontFamily: 'monospace',
                                            fontSize: '0.9rem'
                                        }
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 474,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "info-text",
                                        children: "Sends previous bill amount, billing cycle date, and month range"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 483,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 470,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-form-group",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                        htmlFor: "account-balance-url",
                                        className: "ha-form-label",
                                        children: "💰 Account Balance Webhook"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 489,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        type: "url",
                                        id: "account-balance-url",
                                        className: "ha-form-input",
                                        value: accountBalanceUrl,
                                        onChange: (e)=>setAccountBalanceUrl(e.target.value),
                                        placeholder: "https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID",
                                        style: {
                                            fontFamily: 'monospace',
                                            fontSize: '0.9rem'
                                        }
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 492,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "info-text",
                                        children: "Sends current account balance (outstanding amount)"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 501,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 488,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-form-group",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                        htmlFor: "last-payment-url",
                                        className: "ha-form-label",
                                        children: "💳 Last Payment Webhook"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 507,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                        type: "url",
                                        id: "last-payment-url",
                                        className: "ha-form-input",
                                        value: lastPaymentUrl,
                                        onChange: (e)=>setLastPaymentUrl(e.target.value),
                                        placeholder: "https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID",
                                        style: {
                                            fontFamily: 'monospace',
                                            fontSize: '0.9rem'
                                        }
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 510,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "info-text",
                                        children: "Sends last payment amount and date received"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 519,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 506,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                style: {
                                    display: 'flex',
                                    gap: '0.75rem',
                                    flexWrap: 'wrap'
                                },
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        type: "submit",
                                        className: "ha-button ha-button-primary",
                                        disabled: isLoading,
                                        children: isLoading ? 'Saving...' : 'Save Webhooks'
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 525,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                        type: "button",
                                        className: "ha-button",
                                        onClick: handleTest,
                                        disabled: isLoading || !hasAnyWebhook,
                                        style: {
                                            backgroundColor: '#1e88e5',
                                            color: 'white'
                                        },
                                        children: "Test Webhooks"
                                    }, void 0, false, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 528,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 524,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 451,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "info-text",
                        style: {
                            marginTop: '1rem',
                            padding: '0.75rem',
                            backgroundColor: '#1a1a1a',
                            borderRadius: '4px',
                            border: '1px solid #333'
                        },
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                children: "📋 How it works:"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 541,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                                style: {
                                    marginTop: '0.5rem',
                                    marginBottom: 0,
                                    paddingLeft: '1.25rem'
                                },
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                children: "Smart Change Detection:"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 543,
                                                columnNumber: 17
                                            }, this),
                                            " Webhooks are automatically sent only when values change by comparing with previous scrapes in the database"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 543,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                children: "Test Webhooks:"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 544,
                                                columnNumber: 17
                                            }, this),
                                            " Instantly sends the latest scraped data to all configured webhooks (bypasses change detection for testing)"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 544,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                                children: "Account Ledger:"
                                            }, void 0, false, {
                                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                lineNumber: 545,
                                                columnNumber: 17
                                            }, this),
                                            " View full history of all scrapes and changes on the Account Ledger page"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                        lineNumber: 545,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 542,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 540,
                        columnNumber: 9
                    }, this),
                    message && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card ha-card-".concat(message.type === 'error' ? 'error' : 'status'),
                        style: {
                            marginTop: '1rem'
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-card-content",
                            children: message.text
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                            lineNumber: 551,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 550,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card",
                        style: {
                            marginTop: '1.5rem',
                            backgroundColor: '#1e1e1e',
                            border: '1px solid #333'
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-card-content",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h4", {
                                    style: {
                                        marginTop: 0,
                                        marginBottom: '0.75rem',
                                        fontSize: '0.95rem'
                                    },
                                    children: "Webhook Payload Examples"
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 559,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    style: {
                                        marginBottom: '1rem'
                                    },
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                            style: {
                                                fontSize: '0.9rem'
                                            },
                                            children: "Latest Bill:"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 562,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                                            style: {
                                                backgroundColor: '#0a0a0a',
                                                padding: '0.75rem',
                                                borderRadius: '4px',
                                                fontSize: '0.8rem',
                                                overflow: 'auto',
                                                margin: '0.5rem 0 0 0'
                                            },
                                            children: '{\n  "event_type": "latest_bill",\n  "timestamp": "2026-01-23T12:00:00",\n  "data": {\n    "bill_total": "$123.45",\n    "bill_cycle_date": "January 15, 2026",\n    "month_range": "Dec 16 - Jan 15"\n  }\n}'
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 563,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 561,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    style: {
                                        marginBottom: '1rem'
                                    },
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                            style: {
                                                fontSize: '0.9rem'
                                            },
                                            children: "Account Balance:"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 584,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                                            style: {
                                                backgroundColor: '#0a0a0a',
                                                padding: '0.75rem',
                                                borderRadius: '4px',
                                                fontSize: '0.8rem',
                                                overflow: 'auto',
                                                margin: '0.5rem 0 0 0'
                                            },
                                            children: '{\n  "event_type": "account_balance",\n  "timestamp": "2026-01-23T12:00:00",\n  "data": {\n    "account_balance": 123.45,\n    "account_balance_raw": "$123.45"\n  }\n}'
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 585,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 583,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                            style: {
                                                fontSize: '0.9rem'
                                            },
                                            children: "Last Payment:"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 605,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                                            style: {
                                                backgroundColor: '#0a0a0a',
                                                padding: '0.75rem',
                                                borderRadius: '4px',
                                                fontSize: '0.8rem',
                                                overflow: 'auto',
                                                margin: '0.5rem 0 0 0'
                                            },
                                            children: '{\n  "event_type": "last_payment",\n  "timestamp": "2026-01-23T12:00:00",\n  "data": {\n    "amount": "$123.45",\n    "payment_date": "1/15/2026",\n    "bill_cycle_date": "1/10/2026",\n    "description": "Payment Received"\n  }\n}'
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 606,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 604,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                            lineNumber: 558,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 557,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 446,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
        lineNumber: 441,
        columnNumber: 5
    }, this);
}
_s1(WebhooksTab, "GdrIwQYK/Dn7+NENq23NrnVrAVM=");
_c1 = WebhooksTab;
function AutomatedScrapeTab() {
    _s2();
    const [enabled, setEnabled] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [hours, setHours] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('0');
    const [minutes, setMinutes] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('0');
    const [seconds, setSeconds] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('0');
    const [isLoading, setIsLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [message, setMessage] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [status, setStatus] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AutomatedScrapeTab.useEffect": ()=>{
            loadSchedule();
        }
    }["AutomatedScrapeTab.useEffect"], []);
    const loadSchedule = async ()=>{
        try {
            const response = await fetch("".concat(API_BASE_URL, "/automated-schedule"));
            if (response.ok) {
                const data = await response.json();
                setStatus(data);
                if (data.enabled) {
                    setEnabled(true);
                    const totalSeconds = data.frequency || 0;
                    setHours(Math.floor(totalSeconds / 3600).toString());
                    setMinutes(Math.floor(totalSeconds % 3600 / 60).toString());
                    setSeconds((totalSeconds % 60).toString());
                }
            }
        } catch (error) {
            console.error('Failed to load schedule:', error);
        }
    };
    const handleSave = async (e)=>{
        e.preventDefault();
        setIsLoading(true);
        setMessage(null);
        try {
            const totalSeconds = parseInt(hours) * 3600 + parseInt(minutes) * 60 + parseInt(seconds);
            if (totalSeconds <= 0) {
                setMessage({
                    type: 'error',
                    text: 'Frequency must be greater than 0'
                });
                setIsLoading(false);
                return;
            }
            const response = await fetch("".concat(API_BASE_URL, "/automated-schedule"), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    enabled,
                    frequency: totalSeconds
                })
            });
            if (response.ok) {
                setMessage({
                    type: 'success',
                    text: 'Automated scrape schedule saved successfully!'
                });
                await loadSchedule();
            } else {
                const errorData = await response.json().catch(()=>({}));
                setMessage({
                    type: 'error',
                    text: errorData.error || 'Failed to save schedule'
                });
            }
        } catch (error) {
            setMessage({
                type: 'error',
                text: 'Failed to connect to API. Make sure the Python service is running.'
            });
        } finally{
            setIsLoading(false);
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "ha-card",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card-header",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        className: "ha-card-icon",
                        children: "⏰"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 707,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                        children: "Automated Scrape Schedule"
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 708,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 706,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card-content",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                        onSubmit: handleSave,
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "ha-form-group",
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    style: {
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        cursor: 'pointer'
                                    },
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            type: "checkbox",
                                            checked: enabled,
                                            onChange: (e)=>setEnabled(e.target.checked),
                                            style: {
                                                width: '18px',
                                                height: '18px',
                                                cursor: 'pointer'
                                            }
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 714,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            children: "Enable Automated Scraping"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 720,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 713,
                                    columnNumber: 13
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 712,
                                columnNumber: 11
                            }, this),
                            enabled && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "ha-form-group",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                            className: "ha-form-label",
                                            children: "Scrape Frequency"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 727,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            style: {
                                                display: 'flex',
                                                gap: '1rem',
                                                alignItems: 'flex-start'
                                            },
                                            children: [
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    style: {
                                                        flex: 1
                                                    },
                                                    children: [
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                            htmlFor: "hours",
                                                            className: "ha-form-label",
                                                            style: {
                                                                fontSize: '0.85rem'
                                                            },
                                                            children: "Hours"
                                                        }, void 0, false, {
                                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                            lineNumber: 730,
                                                            columnNumber: 21
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                            type: "number",
                                                            id: "hours",
                                                            className: "ha-form-input",
                                                            min: "0",
                                                            max: "23",
                                                            value: hours,
                                                            onChange: (e)=>setHours(e.target.value),
                                                            required: true
                                                        }, void 0, false, {
                                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                            lineNumber: 731,
                                                            columnNumber: 21
                                                        }, this)
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                    lineNumber: 729,
                                                    columnNumber: 19
                                                }, this),
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    style: {
                                                        flex: 1
                                                    },
                                                    children: [
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                            htmlFor: "minutes",
                                                            className: "ha-form-label",
                                                            style: {
                                                                fontSize: '0.85rem'
                                                            },
                                                            children: "Minutes"
                                                        }, void 0, false, {
                                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                            lineNumber: 743,
                                                            columnNumber: 21
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                            type: "number",
                                                            id: "minutes",
                                                            className: "ha-form-input",
                                                            min: "0",
                                                            max: "59",
                                                            value: minutes,
                                                            onChange: (e)=>setMinutes(e.target.value),
                                                            required: true
                                                        }, void 0, false, {
                                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                            lineNumber: 744,
                                                            columnNumber: 21
                                                        }, this)
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                    lineNumber: 742,
                                                    columnNumber: 19
                                                }, this),
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    style: {
                                                        flex: 1
                                                    },
                                                    children: [
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                                            htmlFor: "seconds",
                                                            className: "ha-form-label",
                                                            style: {
                                                                fontSize: '0.85rem'
                                                            },
                                                            children: "Seconds"
                                                        }, void 0, false, {
                                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                            lineNumber: 756,
                                                            columnNumber: 21
                                                        }, this),
                                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                            type: "number",
                                                            id: "seconds",
                                                            className: "ha-form-input",
                                                            min: "0",
                                                            max: "59",
                                                            value: seconds,
                                                            onChange: (e)=>setSeconds(e.target.value),
                                                            required: true
                                                        }, void 0, false, {
                                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                            lineNumber: 757,
                                                            columnNumber: 21
                                                        }, this)
                                                    ]
                                                }, void 0, true, {
                                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                                    lineNumber: 755,
                                                    columnNumber: 19
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 728,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            className: "info-text",
                                            style: {
                                                marginTop: '0.5rem'
                                            },
                                            children: [
                                                "Scraper will run automatically every ",
                                                hours,
                                                ":",
                                                String(minutes).padStart(2, '0'),
                                                ":",
                                                String(seconds).padStart(2, '0')
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                            lineNumber: 769,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 726,
                                    columnNumber: 15
                                }, this)
                            }, void 0, false),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                type: "submit",
                                className: "ha-button ha-button-primary",
                                disabled: isLoading,
                                children: isLoading ? 'Saving...' : 'Save Schedule'
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                lineNumber: 776,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 711,
                        columnNumber: 9
                    }, this),
                    message && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card ha-card-".concat(message.type === 'error' ? 'error' : 'status'),
                        style: {
                            marginTop: '1rem'
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-card-content",
                            children: message.text
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                            lineNumber: 783,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 782,
                        columnNumber: 11
                    }, this),
                    status && status.enabled && status.nextRun && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card ha-card-status",
                        style: {
                            marginTop: '1rem'
                        },
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-card-content",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Next scheduled run:"
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                                    lineNumber: 792,
                                    columnNumber: 15
                                }, this),
                                " ",
                                new Date(status.nextRun).toLocaleString()
                            ]
                        }, void 0, true, {
                            fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                            lineNumber: 791,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                        lineNumber: 790,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/Settings.tsx",
                lineNumber: 710,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/coned-scraper/app/components/Settings.tsx",
        lineNumber: 705,
        columnNumber: 5
    }, this);
}
_s2(AutomatedScrapeTab, "MXh7ynuXqgCLbe9ecrdk/DIACEU=");
_c2 = AutomatedScrapeTab;
var _c, _c1, _c2;
__turbopack_context__.k.register(_c, "Settings");
__turbopack_context__.k.register(_c1, "WebhooksTab");
__turbopack_context__.k.register(_c2, "AutomatedScrapeTab");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/coned-scraper/app/components/AccountLedger.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>AccountLedger
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
'use client';
;
const API_BASE_URL = __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_URL || '/api';
function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        const dateStr = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        const timeStr = date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
        return {
            date: dateStr,
            time: timeStr
        };
    } catch (e) {
        return {
            date: timestamp,
            time: ''
        };
    }
}
function AccountLedger(param) {
    let { onNavigate } = param;
    var _latestData_data, _latestData_data1;
    _s();
    const [scrapedData, setScrapedData] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [isLoading, setIsLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    const [apiError, setApiError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const loadScrapedData = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AccountLedger.useCallback[loadScrapedData]": async ()=>{
            try {
                const response = await fetch("".concat(API_BASE_URL, "/scraped-data?limit=50"));
                if (response.ok) {
                    const data = await response.json();
                    setScrapedData(data.data || []);
                    setApiError(null);
                } else {
                    setApiError('Failed to load scraped data');
                }
            } catch (error) {
                setApiError('Cannot connect to Python service. Make sure it\'s running on port 8000.');
            } finally{
                setIsLoading(false);
            }
        }
    }["AccountLedger.useCallback[loadScrapedData]"], []);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AccountLedger.useEffect": ()=>{
            loadScrapedData();
            // Refresh every 30 seconds
            const interval = setInterval(loadScrapedData, 30000);
            return ({
                "AccountLedger.useEffect": ()=>clearInterval(interval)
            })["AccountLedger.useEffect"];
        }
    }["AccountLedger.useEffect"], [
        loadScrapedData
    ]);
    if (isLoading) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            style: {
                padding: '4rem 2rem',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '400px'
            },
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                    src: "/images/ajax-loader.gif",
                    alt: "Loading",
                    style: {
                        width: '64px',
                        height: '64px',
                        marginBottom: '1.5rem'
                    }
                }, void 0, false, {
                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                    lineNumber: 80,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    style: {
                        color: '#666',
                        fontSize: '1rem',
                        marginTop: '1rem'
                    },
                    children: "Loading account ledger..."
                }, void 0, false, {
                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                    lineNumber: 89,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
            lineNumber: 71,
            columnNumber: 7
        }, this);
    }
    if (apiError) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            style: {
                padding: '2rem',
                textAlign: 'center',
                color: '#d32f2f'
            },
            children: apiError
        }, void 0, false, {
            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
            lineNumber: 98,
            columnNumber: 7
        }, this);
    }
    if (scrapedData.length === 0) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            style: {
                padding: '4rem 2rem',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '400px'
            },
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                    src: "/images/ajax-loader.gif",
                    alt: "Setup Required",
                    style: {
                        width: '80px',
                        height: '80px',
                        marginBottom: '2rem',
                        opacity: 0.8
                    }
                }, void 0, false, {
                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                    lineNumber: 115,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                    style: {
                        fontSize: '1.5rem',
                        fontWeight: 600,
                        color: '#333',
                        marginBottom: '1rem'
                    },
                    children: "No Account Data Yet"
                }, void 0, false, {
                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                    lineNumber: 125,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    style: {
                        color: '#666',
                        fontSize: '1rem',
                        maxWidth: '500px',
                        lineHeight: '1.6',
                        marginBottom: '2rem'
                    },
                    children: "To get started, please configure your credentials in Settings and run the scraper from the Console."
                }, void 0, false, {
                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                    lineNumber: 133,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    style: {
                        display: 'flex',
                        gap: '1rem',
                        justifyContent: 'center',
                        flexWrap: 'wrap'
                    },
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            onClick: ()=>onNavigate === null || onNavigate === void 0 ? void 0 : onNavigate('settings'),
                            style: {
                                padding: '0.75rem 1.5rem',
                                backgroundColor: '#03a9f4',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '1rem',
                                cursor: 'pointer',
                                fontWeight: 500,
                                transition: 'background-color 0.2s'
                            },
                            onMouseOver: (e)=>e.currentTarget.style.backgroundColor = '#0288d1',
                            onMouseOut: (e)=>e.currentTarget.style.backgroundColor = '#03a9f4',
                            children: "⚙️ Go to Settings"
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                            lineNumber: 148,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                            onClick: ()=>onNavigate === null || onNavigate === void 0 ? void 0 : onNavigate('console'),
                            style: {
                                padding: '0.75rem 1.5rem',
                                backgroundColor: '#4caf50',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '1rem',
                                cursor: 'pointer',
                                fontWeight: 500,
                                transition: 'background-color 0.2s'
                            },
                            onMouseOver: (e)=>e.currentTarget.style.backgroundColor = '#45a049',
                            onMouseOut: (e)=>e.currentTarget.style.backgroundColor = '#4caf50',
                            children: "📊 Go to Console"
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                            lineNumber: 166,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                    lineNumber: 142,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
            lineNumber: 106,
            columnNumber: 7
        }, this);
    }
    const latestData = scrapedData[0];
    const timestamp = formatTimestamp(latestData.timestamp);
    const accountBalance = ((_latestData_data = latestData.data) === null || _latestData_data === void 0 ? void 0 : _latestData_data.account_balance) || '-';
    const screenshotPath = latestData.screenshot_path;
    const billHistory = (_latestData_data1 = latestData.data) === null || _latestData_data1 === void 0 ? void 0 : _latestData_data1.bill_history;
    // Group bills and payments correctly
    const bills = [];
    const payments = [];
    if (billHistory === null || billHistory === void 0 ? void 0 : billHistory.ledger) {
        billHistory.ledger.forEach((entry)=>{
            if (entry.type === 'bill') {
                bills.push(entry);
            } else if (entry.type === 'payment') {
                payments.push(entry);
            }
        });
    }
    // Sort bills by date (newest first)
    bills.sort((a, b)=>{
        try {
            const dateA = new Date(a.bill_cycle_date || a.bill_date || 0);
            const dateB = new Date(b.bill_cycle_date || b.bill_date || 0);
            return dateB.getTime() - dateA.getTime();
        } catch (e) {
            return 0;
        }
    });
    // Sort payments by date (newest first)
    payments.sort((a, b)=>{
        try {
            const dateA = new Date(a.bill_cycle_date || 0);
            const dateB = new Date(b.bill_cycle_date || 0);
            return dateB.getTime() - dateA.getTime();
        } catch (e) {
            return 0;
        }
    });
    // Group payments under their corresponding bills
    const groupedBills = [];
    const assignedPaymentIndices = new Set();
    bills.forEach((bill, billIndex)=>{
        try {
            const billCycleDateStr = bill.bill_cycle_date || bill.bill_date || '';
            const billCycleEndDate = new Date(billCycleDateStr);
            const previousBillCycleEndDate = billIndex > 0 ? new Date(bills[billIndex - 1].bill_cycle_date || bills[billIndex - 1].bill_date || 0) : null;
            const billPayments = [];
            payments.forEach((payment, paymentIndex)=>{
                if (assignedPaymentIndices.has(paymentIndex)) {
                    return;
                }
                try {
                    const paymentDateStr = payment.bill_cycle_date || '';
                    const paymentDate = new Date(paymentDateStr);
                    let belongsToThisBill = false;
                    if (previousBillCycleEndDate === null) {
                        belongsToThisBill = paymentDate > billCycleEndDate;
                    } else {
                        belongsToThisBill = paymentDate > billCycleEndDate && paymentDate <= previousBillCycleEndDate;
                    }
                    if (belongsToThisBill) {
                        billPayments.push(payment);
                        assignedPaymentIndices.add(paymentIndex);
                    }
                } catch (e) {
                    console.warn('Failed to parse payment date:', payment, e);
                }
            });
            billPayments.sort((a, b)=>{
                try {
                    const dateA = new Date(a.bill_cycle_date || 0);
                    const dateB = new Date(b.bill_cycle_date || 0);
                    return dateB.getTime() - dateA.getTime();
                } catch (e) {
                    return 0;
                }
            });
            groupedBills.push({
                bill,
                payments: billPayments
            });
        } catch (e) {
            console.warn('Failed to parse bill date:', bill, e);
            groupedBills.push({
                bill,
                payments: []
            });
        }
    });
    // Remove duplicate bills
    const seenBillDates = new Set();
    const uniqueGroupedBills = groupedBills.filter((group)=>{
        const billDate = group.bill.bill_cycle_date || group.bill.bill_date || '';
        if (seenBillDates.has(billDate)) {
            return false;
        }
        seenBillDates.add(billDate);
        return true;
    });
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "ha-ledger",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card ha-card-summary",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-header",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "ha-card-icon",
                                children: "💰"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                lineNumber: 309,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                children: "Account Summary"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                lineNumber: 310,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                        lineNumber: 308,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-content",
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-summary-grid",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Date:"
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 314,
                                    columnNumber: 13
                                }, this),
                                " ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    children: timestamp.date
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 314,
                                    columnNumber: 36
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Time:"
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 315,
                                    columnNumber: 13
                                }, this),
                                " ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    children: timestamp.time
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 315,
                                    columnNumber: 36
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                    children: "Account Balance:"
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 316,
                                    columnNumber: 13
                                }, this),
                                " ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "ha-summary-balance",
                                    children: accountBalance
                                }, void 0, false, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 316,
                                    columnNumber: 47
                                }, this),
                                screenshotPath && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("strong", {
                                            children: "Screenshot:"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                            lineNumber: 319,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("a", {
                                            href: "".concat(API_BASE_URL, "/screenshot/").concat(screenshotPath.split('/').pop() || screenshotPath),
                                            target: "_blank",
                                            rel: "noopener noreferrer",
                                            className: "ha-button ha-button-primary",
                                            style: {
                                                fontSize: '0.7rem',
                                                padding: '0.4rem 0.75rem',
                                                textDecoration: 'none',
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.4rem'
                                            },
                                            children: [
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                                                    src: "/images/Coned_snapshot.svg",
                                                    alt: "Screenshot",
                                                    style: {
                                                        width: '16px',
                                                        height: '16px'
                                                    }
                                                }, void 0, false, {
                                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                    lineNumber: 327,
                                                    columnNumber: 19
                                                }, this),
                                                "View Account Balance Screenshot"
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                            lineNumber: 320,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                            lineNumber: 313,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                        lineNumber: 312,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                lineNumber: 307,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-card ha-card-ledger",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-header",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "ha-card-icon",
                                children: "📋"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                lineNumber: 338,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                children: "Bill History Ledger"
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                lineNumber: 339,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                        lineNumber: 337,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "ha-card-content",
                        children: uniqueGroupedBills.length > 0 ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            children: uniqueGroupedBills.map((group, idx)=>{
                                const bill = group.bill;
                                const payments = group.payments;
                                const cycleKey = bill.bill_cycle_date || bill.bill_date || 'Unknown';
                                return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "ha-bill-card",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            className: "ha-bill-header",
                                            children: [
                                                "Bill Cycle: ",
                                                cycleKey,
                                                (bill === null || bill === void 0 ? void 0 : bill.month_range) && " (".concat(bill.month_range, ")")
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                            lineNumber: 351,
                                            columnNumber: 21
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            className: "ha-bill-entry",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "ha-bill-content",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                        style: {
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.6rem',
                                                            flexWrap: 'wrap'
                                                        },
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                className: "ha-bill-badge",
                                                                children: "Bill"
                                                            }, void 0, false, {
                                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                lineNumber: 359,
                                                                columnNumber: 27
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                children: [
                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                        style: {
                                                                            fontWeight: 600,
                                                                            marginBottom: '0.15rem',
                                                                            fontSize: '0.8rem'
                                                                        },
                                                                        children: bill.month_range || 'Bill'
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                        lineNumber: 361,
                                                                        columnNumber: 29
                                                                    }, this),
                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                        style: {
                                                                            fontSize: '0.7rem',
                                                                            color: '#666'
                                                                        },
                                                                        children: bill.bill_date ? new Date(bill.bill_date).toLocaleDateString('en-US', {
                                                                            year: 'numeric',
                                                                            month: 'short',
                                                                            day: 'numeric'
                                                                        }) : cycleKey
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                        lineNumber: 364,
                                                                        columnNumber: 29
                                                                    }, this)
                                                                ]
                                                            }, void 0, true, {
                                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                lineNumber: 360,
                                                                columnNumber: 27
                                                            }, this)
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                        lineNumber: 358,
                                                        columnNumber: 25
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                        className: "ha-bill-amount",
                                                        children: bill.bill_total || '-'
                                                    }, void 0, false, {
                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                        lineNumber: 369,
                                                        columnNumber: 25
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                lineNumber: 357,
                                                columnNumber: 23
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                            lineNumber: 356,
                                            columnNumber: 21
                                        }, this),
                                        payments.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            children: payments.map((payment, paymentIdx)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    className: "ha-payment-entry",
                                                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                        style: {
                                                            display: 'flex',
                                                            justifyContent: 'space-between',
                                                            alignItems: 'center',
                                                            flexWrap: 'wrap',
                                                            gap: '0.5rem'
                                                        },
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                style: {
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: '0.5rem',
                                                                    flexWrap: 'wrap'
                                                                },
                                                                children: [
                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                        className: "ha-payment-badge",
                                                                        children: "Payment"
                                                                    }, void 0, false, {
                                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                        lineNumber: 381,
                                                                        columnNumber: 33
                                                                    }, this),
                                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                        children: [
                                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                                style: {
                                                                                    fontWeight: 500,
                                                                                    marginBottom: '0.1rem',
                                                                                    fontSize: '0.75rem'
                                                                                },
                                                                                children: payment.description || 'Payment Received'
                                                                            }, void 0, false, {
                                                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                                lineNumber: 383,
                                                                                columnNumber: 35
                                                                            }, this),
                                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                                style: {
                                                                                    fontSize: '0.65rem',
                                                                                    color: '#666'
                                                                                },
                                                                                children: payment.bill_cycle_date || cycleKey
                                                                            }, void 0, false, {
                                                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                                lineNumber: 386,
                                                                                columnNumber: 35
                                                                            }, this)
                                                                        ]
                                                                    }, void 0, true, {
                                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                        lineNumber: 382,
                                                                        columnNumber: 33
                                                                    }, this)
                                                                ]
                                                            }, void 0, true, {
                                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                lineNumber: 380,
                                                                columnNumber: 31
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                                className: "ha-payment-amount",
                                                                children: payment.amount || '-'
                                                            }, void 0, false, {
                                                                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                                lineNumber: 391,
                                                                columnNumber: 31
                                                            }, this)
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                        lineNumber: 379,
                                                        columnNumber: 29
                                                    }, this)
                                                }, paymentIdx, false, {
                                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                                    lineNumber: 378,
                                                    columnNumber: 27
                                                }, this))
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                            lineNumber: 376,
                                            columnNumber: 23
                                        }, this)
                                    ]
                                }, "".concat(cycleKey, "-").concat(idx), true, {
                                    fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                                    lineNumber: 350,
                                    columnNumber: 19
                                }, this);
                            })
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                            lineNumber: 343,
                            columnNumber: 13
                        }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-empty-state",
                            children: "No bill history ledger data available. Run the scraper to collect data."
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                            lineNumber: 404,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                        lineNumber: 341,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
                lineNumber: 336,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/coned-scraper/app/components/AccountLedger.tsx",
        lineNumber: 306,
        columnNumber: 5
    }, this);
}
_s(AccountLedger, "qEgFoiDzlMbGoM51aB1xDyWv5zg=");
_c = AccountLedger;
var _c;
__turbopack_context__.k.register(_c, "AccountLedger");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/coned-scraper/app/app/page.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>Home
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$components$2f$Dashboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/components/Dashboard.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$components$2f$Settings$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/components/Settings.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$components$2f$AccountLedger$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/components/AccountLedger.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
'use client';
;
;
;
;
function Home() {
    _s();
    const [activeTab, setActiveTab] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('account-ledger');
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "ha-container",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-header",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "ha-header-content",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "ha-logo-container",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                                src: "/images/logo.svg",
                                alt: "ConEd Logo",
                                width: 100,
                                height: 20,
                                style: {
                                    filter: 'brightness(0) invert(1)'
                                }
                            }, void 0, false, {
                                fileName: "[project]/coned-scraper/app/app/page.tsx",
                                lineNumber: 16,
                                columnNumber: 13
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                            lineNumber: 15,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                            className: "ha-nav",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    className: "ha-nav-button ".concat(activeTab === 'account-ledger' ? 'active' : ''),
                                    onClick: ()=>setActiveTab('account-ledger'),
                                    "aria-label": "Account Ledger",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "ha-nav-icon",
                                            children: "📋"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                                            lineNumber: 30,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            children: "Account Ledger"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                                            lineNumber: 31,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/app/page.tsx",
                                    lineNumber: 25,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    className: "ha-nav-button ".concat(activeTab === 'console' ? 'active' : ''),
                                    onClick: ()=>setActiveTab('console'),
                                    "aria-label": "Console",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "ha-nav-icon",
                                            children: "📊"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                                            lineNumber: 38,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            children: "Console"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                                            lineNumber: 39,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/app/page.tsx",
                                    lineNumber: 33,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    className: "ha-nav-button ".concat(activeTab === 'settings' ? 'active' : ''),
                                    onClick: ()=>setActiveTab('settings'),
                                    "aria-label": "Settings",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "ha-nav-icon",
                                            children: "⚙️"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                                            lineNumber: 46,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            children: "Settings"
                                        }, void 0, false, {
                                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                                            lineNumber: 47,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/coned-scraper/app/app/page.tsx",
                                    lineNumber: 41,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/coned-scraper/app/app/page.tsx",
                            lineNumber: 24,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/coned-scraper/app/app/page.tsx",
                    lineNumber: 14,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/coned-scraper/app/app/page.tsx",
                lineNumber: 13,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "ha-content",
                children: [
                    activeTab === 'console' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$components$2f$Dashboard$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {}, void 0, false, {
                        fileName: "[project]/coned-scraper/app/app/page.tsx",
                        lineNumber: 54,
                        columnNumber: 37
                    }, this),
                    activeTab === 'account-ledger' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$components$2f$AccountLedger$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                        onNavigate: (tab)=>setActiveTab(tab)
                    }, void 0, false, {
                        fileName: "[project]/coned-scraper/app/app/page.tsx",
                        lineNumber: 55,
                        columnNumber: 44
                    }, this),
                    activeTab === 'settings' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$components$2f$Settings$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {}, void 0, false, {
                        fileName: "[project]/coned-scraper/app/app/page.tsx",
                        lineNumber: 56,
                        columnNumber: 38
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/coned-scraper/app/app/page.tsx",
                lineNumber: 53,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/coned-scraper/app/app/page.tsx",
        lineNumber: 12,
        columnNumber: 5
    }, this);
}
_s(Home, "DKN+g4yol7V05OYvcZYcuWTqPyo=");
_c = Home;
var _c;
__turbopack_context__.k.register(_c, "Home");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=coned-scraper_app_be556a36._.js.map