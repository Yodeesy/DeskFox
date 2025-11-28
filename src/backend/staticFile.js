import { config, NotFound404 } from './src/backend/init.js'

export const handleStaticFile = async (req) => {
    const url = new URL(req.url)
    const path = decodeURIComponent(url.pathname)

    // 限制在 static 目录下
    const filePath = `${config.staticpath}${path === '/' ? '/index.html' : path
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
