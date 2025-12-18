// deno-lint-ignore-file
// import { handleStaticFile } from './staticFile.js'
// const config = JSON.parse(Deno.readTextFileSync('./src/backend/config.json'))
import { crypto } from 'https://deno.land/std@0.224.0/crypto/mod.ts'

// 计算字符串的 SHA-256
const sha256 = async (text) => {
    const encoder = new TextEncoder()
    const data = encoder.encode(text)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join(
        '',
    )
    return hashHex
}

const config = {
    'pathname': '/stories',
    'staticpath': './src/backend/static',
}
const NotFound404 = () => new Response('404 Not Found', { status: 404 })

const handleStaticFile = async (req) => {
    const url = new URL(req.url)
    const path = decodeURIComponent(url.pathname)

    // 限制在 static 目录下
    const filePath = `${config.staticpath}${
        path === '/' ? '/index.html' : path
    }`

    try {
        await Deno.stat(filePath)
        const file = await Deno.readFile(filePath)

        // 简单的 MIME 类型映射
        const ext = filePath.split('.').pop()
        const mime = {
            html: 'text/html',
            css: 'text/css',
            js: 'application/javascript',
            png: 'image/png',
            jpg: 'image/jpg',
            ico: 'image/x-icon',
        }[ext ?? ''] || 'application/octet-stream'

        return new Response(file, {
            headers: { 'Content-Type': mime },
        })
    } catch (err) {
        if (path === '/.well-known/appspecific/com.chrome.devtools.json') {
            return NotFound404()
        }
        console.log(err)
        return NotFound404()
    }
}

const handleDataGet = async (req) => {
    const url = new URL(req.url)
    const index = url.searchParams.get('index')
    if (!index) return new Response('404 Not Found', { status: 404 })
    const kv = await Deno.openKv()

    const result = await kv.get(['zst', index.toString()])
    if (result.value) {
        return new Response(JSON.stringify(result.value))
    } else {
        return new Response('404 Not Found', { status: 404 })
    }
}

const SHA256_VALUE =
    '76c7b9b4e7bb7f4f0b5ad2120526cda883c01b8a62c40d750239da24ce4a6640'

const handleDataUpdate = async (req) => {
    const url = new URL(req.url)
    try {
        const { index, data, key } = await req.json()
        if (!index || !data || !key) {
            return new Response('无效的 JSON 请求体', { status: 400 })
        }
        //验证密码
        let sha = await sha256(key)
        if (sha !== SHA256_VALUE) {
            return new Response('密码错误', { status: 401 })
        }

        const kv = await Deno.openKv()

        const setResult = await kv.set(['zst', index.toString()], data)
        return new Response(`写入成功`)
    } catch (err) {
        console.log(err)
        return new Response(`写入失败, ${JSON.stringify(err)}`, { status: 500 })
    }
}

export const handleZST = async (req) => {
    if (req.method === 'GET') {
        return await handleDataGet(req)
    }
    if (req.method === 'POST') {
        return await handleDataUpdate(req)
    }
    return new Response('404 Not Found', { status: 404 })
}

Deno.serve({
    onListen({ port, hostname }) {
        console.log(`Server running on http://${hostname}:${port}`)
    },
}, async (req) => {
    const url = new URL(req.url)
    if (url.pathname.startsWith(config.pathname)) return await handleZST(req)
    return await handleStaticFile(req)
})
