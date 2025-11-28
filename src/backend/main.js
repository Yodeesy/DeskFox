// deno-lint-ignore-file
import { handleStaticFile } from './src/backend/staticFile.js'
const config = JSON.parse(Deno.readTextFileSync('./src/backend/config.json'))

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

const handleDataUpdate = async (req) => {
    const url = new URL(req.url)
    try {
        const { index, data } = await req.json()
        if (!index || !data) {
            return new Response('无效的 JSON 请求体', { status: 400 })
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
