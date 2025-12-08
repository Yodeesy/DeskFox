const express = require('express')
const path = require('path')


const app = express()


const staticDir = path.join(__dirname, 'static')
app.use(express.static(staticDir))






const port = 8080
app.listen(port, () => {
    console.log(`server is running at http://localhost:${port}`)
})