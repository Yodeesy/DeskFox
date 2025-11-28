## Deskfox Web服务API文档

### url路径

在`config.json`文件中可以配置你喜欢的路径名，默认端口号是8000（当然，可以改）。

```json
// congfig.json
{
    "pathname": "/zst"
}
```

### 获取数据API

#### 请求路径

开发环境： `http://127.0.0.1:8000/zst`

生产环境： `https://域名/zst`

#### 请求方法

GET

#### URL请求参数

`index`: 想要获取的数据的索引

```
//示例
//获取索引为1的数据
http://127.0.0.1:8000/zst?index=1
```

#### 返回类型

content-type: text/plain;charset=UTF-8

### 写入数据API

#### 请求路径

开发环境： `http://127.0.0.1:8000/zst`

生产环境： `https://域名/zst`

#### 请求方法

POST

#### JSON请求体参数

`index`: 想要写入的数据的索引

`data`: 写入的数据

```json
//示例
//请求体
{
    "index": "1",
    "data": "Hello, deskfox!"
}
```

#### 返回类型

返回两句话，写入成功或写入失败
