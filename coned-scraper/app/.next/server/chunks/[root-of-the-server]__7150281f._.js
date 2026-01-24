module.exports = [
"[project]/coned-scraper/app/.next-internal/server/app/api/[...slug]/route/actions.js [app-rsc] (server actions loader, ecmascript)", ((__turbopack_context__, module, exports) => {

}),
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/action-async-storage.external.js [external] (next/dist/server/app-render/action-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/action-async-storage.external.js", () => require("next/dist/server/app-render/action-async-storage.external.js"));

module.exports = mod;
}),
"[project]/coned-scraper/app/app/api/[...slug]/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "DELETE",
    ()=>DELETE,
    "GET",
    ()=>GET,
    "POST",
    ()=>POST
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/coned-scraper/app/node_modules/next/server.js [app-route] (ecmascript)");
;
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';
async function GET(request, context) {
    const params = await context.params;
    const slug = params.slug || [];
    const path = slug.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${PYTHON_API_URL}/api/${path}${searchParams ? `?${searchParams}` : ''}`;
    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            cache: 'no-store'
        });
        if (!response.ok) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: `API error: ${response.status} ${response.statusText}`
            }, {
                status: response.status
            });
        }
        // Check if response is an image
        const contentType = response.headers.get('content-type') || '';
        if (contentType.startsWith('image/')) {
            const blob = await response.blob();
            return new __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"](blob, {
                headers: {
                    'Content-Type': contentType,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            });
        }
        // Otherwise, parse as JSON
        const data = await response.json();
        return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(data);
    } catch (error) {
        console.error('Proxy error:', error);
        return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: 'Failed to connect to Python API service'
        }, {
            status: 503
        });
    }
}
async function POST(request, context) {
    const params = await context.params;
    const slug = params.slug || [];
    const path = slug.join('/');
    const url = `${PYTHON_API_URL}/api/${path}`;
    try {
        const body = await request.json().catch(()=>null);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: body ? JSON.stringify(body) : undefined
        });
        if (!response.ok) {
            const errorData = await response.json().catch(()=>({}));
            return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: errorData.detail || `API error: ${response.status}`
            }, {
                status: response.status
            });
        }
        const data = await response.json();
        return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(data);
    } catch (error) {
        console.error('Proxy error:', error);
        return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: 'Failed to connect to Python API service'
        }, {
            status: 503
        });
    }
}
async function DELETE(request, context) {
    const params = await context.params;
    const slug = params.slug || [];
    const path = slug.join('/');
    const url = `${PYTHON_API_URL}/api/${path}`;
    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: `API error: ${response.status}`
            }, {
                status: response.status
            });
        }
        const data = await response.json().catch(()=>({
                success: true
            }));
        return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(data);
    } catch (error) {
        console.error('Proxy error:', error);
        return __TURBOPACK__imported__module__$5b$project$5d2f$coned$2d$scraper$2f$app$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: 'Failed to connect to Python API service'
        }, {
            status: 503
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__7150281f._.js.map