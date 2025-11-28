export const config = JSON.parse(Deno.readTextFileSync('./config.json'))

export const NotFound404 = () => new Response('404 Not Found', { status: 404 })
