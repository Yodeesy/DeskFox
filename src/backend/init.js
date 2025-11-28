export const config = JSON.parse(Deno.readTextFileSync('./src/backend/config.json'))

export const NotFound404 = () => new Response('404 Not Found', { status: 404 })
