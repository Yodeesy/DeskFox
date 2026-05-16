// Deno server — serves static site and a /stories KV API.

import { crypto } from 'https://deno.land/std@0.224.0/crypto/mod.ts'

const STORY_WRITE_KEY_HASH = Deno.env.get('STORY_WRITE_KEY_HASH') || ''

const config = {
    pathname: '/stories',
    staticpath: './src/backend/static',
}

// --- Helpers ---

const sha256 = async (text) => {
    const encoder = new TextEncoder()
    const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(text))
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
}

const NotFound404 = () => new Response('404 Not Found', { status: 404 })

const mimeMap = {
    html: 'text/html',
    css: 'text/css',
    js: 'application/javascript',
    json: 'application/json',
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    ico: 'image/x-icon',
    svg: 'image/svg+xml',
    webp: 'image/webp',
    exe: 'application/vnd.microsoft.portable-executable',
}

/** Return a short cache TTL based on file type so assets don't re-download
 *  every page visit.  HTML is never cached; images get 24 h; CSS/JS 1 h. */
function cacheHeader(ext) {
    if (ext === 'html') return 'no-cache'
    if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'ico'
        || ext === 'svg' || ext === 'webp' || ext === 'exe') {
        return 'public, max-age=86400'
    }
    if (ext === 'css' || ext === 'js') return 'public, max-age=3600'
    return 'no-cache'
}

// --- Static-file handler ---

const handleStaticFile = async (req) => {
    const url = new URL(req.url)
    const rawPath = decodeURIComponent(url.pathname)

    // Reject path traversal attempts.
    if (rawPath.includes('..')) return NotFound404()

    const filePath = `${config.staticpath}${
        rawPath === '/' ? '/index.html' : rawPath
    }`

    try {
        await Deno.stat(filePath)
        const file = await Deno.readFile(filePath)

        const ext = (filePath.split('.').pop() || '').toLowerCase()
        const mime = mimeMap[ext] || 'application/octet-stream'

        return new Response(file, {
            headers: {
                'Content-Type': mime,
                'Cache-Control': cacheHeader(ext),
            },
        })
    } catch (err) {
        if (rawPath === '/.well-known/appspecific/com.chrome.devtools.json') {
            return NotFound404()
        }
        console.error('Static file error:', err)
        return NotFound404()
    }
}

// --- /stories API ---

const handleDataGet = async (req) => {
    const url = new URL(req.url)
    const index = url.searchParams.get('index')
    if (!index) return new Response('Missing ?index=', { status: 400 })

    try {
        const kv = await Deno.openKv()
        const result = await kv.get(['zst', index.toString()])
        if (result.value) {
            return new Response(JSON.stringify(result.value))
        }
        return new Response('Not Found', { status: 404 })
    } catch (err) {
        console.error('KV get error:', err)
        return new Response('KV read failed', { status: 500 })
    }
}

const handleDataUpdate = async (req) => {
    try {
        const { index, data, key } = await req.json()
        if (!index || !data || !key) {
            return new Response('Missing index, data, or key', { status: 400 })
        }

        const sha = await sha256(key)
        if (!STORY_WRITE_KEY_HASH || sha !== STORY_WRITE_KEY_HASH) {
            return new Response('Unauthorized', { status: 401 })
        }

        const kv = await Deno.openKv()
        await kv.set(['zst', index.toString()], data)
        return new Response('OK')
    } catch (err) {
        console.error('KV set error:', err)
        return new Response('Write failed', { status: 500 })
    }
}

export const handleZST = async (req) => {
    if (req.method === 'GET') return await handleDataGet(req)
    if (req.method === 'POST') return await handleDataUpdate(req)
    return new Response('Method Not Allowed', { status: 405 })
}

// --- Serve ---

Deno.serve({
    onListen({ port, hostname }) {
        console.log(`Server running on http://${hostname}:${port}`)
    },
}, async (req) => {
    const url = new URL(req.url)
    if (url.pathname.startsWith(config.pathname)) return await handleZST(req)
    return await handleStaticFile(req)
})
