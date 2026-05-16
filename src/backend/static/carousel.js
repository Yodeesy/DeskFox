/** Image carousel with swipe support and auto-play. */

const track = document.querySelector('.carousel-track')
const descriptions = document.querySelectorAll('.des-carousel-track p')
const indicatorsBox = document.querySelector('.indicators')
const prevBtn = document.querySelector('.prev-btn')
const nextBtn = document.querySelector('.next-btn')

let imgs
let indicators
let currentIndex = 0
let autoPlayInterval
let touchStartX = 0
let touchEndX = 0

function init() {
    for (let i = 0; i < 8; i++) {
        const img = document.createElement('img')
        img.src = `./pics/${encodeURIComponent('图片')}${i + 1}.png`
        img.alt = `Screenshot ${i + 1}`

        const span = document.createElement('span')
        span.classList.add('indicator')
        span.dataset.index = i

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

function switchImg(index) {
    imgs.forEach((img) => img.classList.remove('active'))
    indicators.forEach((ind) => ind.classList.remove('active'))
    descriptions.forEach((des) => des.classList.remove('active'))

    imgs[index].classList.add('active')
    indicators[index].classList.add('active')
    descriptions[index].classList.add('active')
    currentIndex = index
}

// --- Button navigation ---
nextBtn.addEventListener('click', () => {
    switchImg((currentIndex + 1) % imgs.length)
})

prevBtn.addEventListener('click', () => {
    switchImg((currentIndex - 1 + imgs.length) % imgs.length)
})

// --- Indicator clicks ---
indicatorsBox.addEventListener('click', (e) => {
    const ind = e.target.closest('.indicator')
    if (!ind) return
    const idx = parseInt(ind.dataset.index, 10)
    if (!Number.isNaN(idx)) switchImg(idx)
})

// --- Touch / swipe support ---
document.querySelector('.carousel-container').addEventListener(
    'touchstart', (e) => { touchStartX = e.changedTouches[0].screenX },
    { passive: true },
)

document.querySelector('.carousel-container').addEventListener(
    'touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX
        const delta = touchStartX - touchEndX
        if (Math.abs(delta) > 40) {
            if (delta > 0) {
                switchImg((currentIndex + 1) % imgs.length)
            } else {
                switchImg((currentIndex - 1 + imgs.length) % imgs.length)
            }
        }
    },
    { passive: true },
)

// --- Auto-play with hover pause ---
function autoPlay() {
    autoPlayInterval = setInterval(() => {
        switchImg((currentIndex + 1) % imgs.length)
    }, 5000)
}

document.querySelector('.carousel-container').addEventListener(
    'mouseenter', () => clearInterval(autoPlayInterval),
)
document.querySelector('.carousel-container').addEventListener(
    'mouseleave', autoPlay,
)

autoPlay()
