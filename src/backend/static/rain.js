// 彩虹色数组（红、橙、黄、绿、蓝、靛、紫）
const colors = [
    '#ff0000', '#ffa500', '#ffff00',
    '#008000', '#0000ff', '#4b0082', '#ee82ee'
]

// 创建雨滴的函数
function createRain() {
    const rain = document.createElement('div')
    rain.classList.add('rain')

    // 随机设置雨滴属性
    const size = Math.random() * 40 + 40 // 雨滴长度
    const posX = Math.random() * 100 // 水平位置
    const duration = Math.random() * 2 + 1 // 下落时间
    const color = colors[Math.floor(Math.random() * colors.length)] // 随机彩虹色

    const glowBlur = size * 0.5 // 模糊度：雨滴越大，发光范围越广
    const glowSpread = 1 // 阴影扩散半径

    // 应用样式
    rain.style.height = `${size}px`
    rain.style.left = `${posX}px`
    rain.style.top = `-${size}px` // 从屏幕顶部外开始
    rain.style.color = color
    rain.style.animation = `fall ${duration}s linear forwards`

    // 多层阴影增强发光感：内阴影+外阴影，颜色与雨滴一致
    rain.style.boxShadow = `
        0 0 ${glowBlur}px ${glowSpread}px ${color}, /* 外发光 */
        inset 0 0 ${glowBlur * 0.5}px ${glowSpread * 0.5}px ${color} /* 内发光（增强中心亮度） */
      `
    // 可选：轻微模糊整体，让发光更柔和
    // rain.style.filter = `blur(0.5px)`
    // rain.style.animation = `fall ${duration}s linear forwards`

    document.getElementById('decBox').appendChild(rain)

    // 雨滴落地后移除元素（避免性能消耗）
    setTimeout(() => {
        rain.remove()
    }, duration * 1000)
}

// 定义下落动画（雨滴从顶部移动到底部）
const style = document.createElement('style')
style.textContent = `
      @keyframes fall {
        to {
          transform: translateY(650px); /* 移动距离为屏幕高度 */
          opacity: 0; /* 落地后消失 */
        }
      }
    `
document.head.appendChild(style)

// 持续创建雨滴
setInterval(createRain, 50)

