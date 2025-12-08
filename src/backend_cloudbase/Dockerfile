# 使用 Node.js 官方镜像作为基础镜像（选择与 express 5.2.1 兼容的版本，建议 Node.js 18+）
FROM node:18-alpine

# 设置工作目录为容器内的 /app（对应宿主机的 src/backend_cloudbase）
WORKDIR /app

# 复制 package.json 和 package-lock.json 到工作目录
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制当前目录（src/backend_cloudbase）下的所有文件到工作目录
COPY . .

# 暴露应用运行的端口（与 server.js 中配置的 8080 一致）
EXPOSE 3000

# 启动命令（运行 server.js）
CMD ["node", "server.js"]