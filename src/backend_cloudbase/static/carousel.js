// deno-lint-ignore-file
const track = document.querySelector('.carousel-track')
const descriptions = document.querySelectorAll('.des-carousel-track p')
const indicatorsBox = document.querySelector('.indicators')
const prevBtn = document.querySelector('.prev-btn')
const nextBtn = document.querySelector('.next-btn')
let imgs, indicators
let currentIndex = 0
let autoPlayInterval

function init() {
    for (let i = 0; i < 8; i++) {
        const img = document.createElement('img')
        img.src = `./pics/图片${i + 1}.png`
        img.alt = `图片${i + 1}`
        const span = document.createElement('span')
        span.classList.add('indicator')
        span['data-index'] = 'i'
        if (i === 0) {
            img.classList.add('active')
            span.classList.add('active')
        }

        track.appendChild(img)
        indicatorsBox.appendChild(span)
    }
    imgs = document.querySelectorAll('.carousel-track img')
    indicators = document.querySelectorAll('.indicator')
}
init()

// 切换图片函数
function switchImg(index) {
    // 移除所有active类
    imgs.forEach((img) => img.classList.remove('active'))
    indicators.forEach((ind) => ind.classList.remove('active'))
    descriptions.forEach((des) => des.classList.remove('active'))
    // 添加当前active类
    imgs[index].classList.add('active')
    indicators[index].classList.add('active')
    descriptions[index].classList.add('active')
    currentIndex = index
}

// 下一张
nextBtn.addEventListener('click', () => {
    let nextIndex = (currentIndex + 1) % imgs.length
    switchImg(nextIndex)
})

// 上一张
prevBtn.addEventListener('click', () => {
    let prevIndex = (currentIndex - 1 + imgs.length) % imgs.length
    switchImg(prevIndex)
})

// 点击指示器切换
indicators.forEach((ind, index) => {
    ind.addEventListener('click', () => switchImg(index))
})

// 自动播放
function autoPlay() {
    autoPlayInterval = setInterval(() => {
        let nextIndex = (currentIndex + 1) % imgs.length
        switchImg(nextIndex)
    }, 5000) // 5秒切换一次
}

// 鼠标悬停暂停自动播放
document.querySelector('.carousel-container').addEventListener(
    'mouseenter',
    () => {
        clearInterval(autoPlayInterval)
    },
)

// 鼠标离开恢复自动播放
document.querySelector('.carousel-container').addEventListener(
    'mouseleave',
    autoPlay,
)

// 初始化自动播放

autoPlay()
