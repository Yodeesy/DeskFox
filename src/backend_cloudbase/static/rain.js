// rain.js - 未来感霓虹雨 (Neon Stream)

// 雨滴容器 ID
const RAIN_CONTAINER_ID = 'fullScreenDecorate';

// 霓虹颜色库
const neonColors = [
    '#ff00ff', // 洋红
    '#00ffff', // 青色
    '#00ff80', // 春绿
    '#ff8000', // 橘红
    '#8000ff'  // 紫色
];

let container;
let containerHeight;
let containerWidth;

// 存储所有雨滴实例
const drops = [];
const maxDrops = 19; // 调整雨滴数量，兼顾性能和密度

/**
 * 获取随机霓虹色
 */
function getRandomColor() {
    return neonColors[Math.floor(Math.random() * neonColors.length)];
}

/**
 * 计算雨滴的 Opacity，实现 淡 -> 强 -> 淡 的效果
 * 使用 Math.sin(x * PI) 曲线，模拟雨滴在视野中划过时的聚焦和模糊
 * @param {number} y - 当前Y座標
 * @returns {number} 0.05 到 0.8 之间的 Opacity 值
 */
function calculateOpacity(y) {
    // 归一化 y 坐标 (0 到 1)
    const normalizedY = y / containerHeight;

    // 使用 Math.sin(x * PI) 实现 0 -> 1 -> 0 曲线
    return Math.sin(normalizedY * Math.PI) * 0.75 + 0.05;
}


// --- Raindrop Class：管理单个雨滴的状态和渲染 ---
class Raindrop {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'rain-drop neon-glow'; // 添加 neon-glow 类

        // 随机属性
        this.size = Math.random() * 40 + 40; // 雨滴长度
        this.speed = 0.25 * (0.8964 + Math.random() * 3); // 随机速度

        // 应用初始样式
        this.element.style.height = `${this.size}px`;
        this.element.style.width = '2px';
        this.element.style.filter = `blur(1.5px)`;
        this.element.style.color = getRandomColor(); // 赋予颜色给 box-shadow

        container.appendChild(this.element);
        this.reset();
    }

    /**
     * 重置雨滴到顶部
     */
    reset() {
        this.y = -Math.random() * containerHeight * 0.5; // 从上方随机位置开始
        this.x = Math.random() * containerWidth;

        this.element.style.left = `${this.x}px`;
        this.element.style.color = getRandomColor(); // 赋予新颜色
        this.speed = 4 + Math.random() * 6;
        this.element.style.height = `${Math.random() * 40 + 40}px`;
    }

    /**
     * 更新雨滴位置和透明度
     */
    update() {
        this.y += this.speed;

        // 计算并设置透明度
        const opacity = calculateOpacity(this.y);
        this.element.style.opacity = opacity;

        // 更新位置
        this.element.style.transform = `translateY(${this.y}px)`;

        // 如果雨滴落到底部，重置其位置
        if (this.y > containerHeight) {
            this.reset();
        }
    }
}


/**
 * 初始化雨滴
 */
function initializeRain() {
    container = document.getElementById(RAIN_CONTAINER_ID);

    if (!container) {
        console.error(`Container #${RAIN_CONTAINER_ID} not found.`);
        return;
    }

    // 确保在初始化时获取正确的容器尺寸
    containerWidth = container.clientWidth;
    containerHeight = container.clientHeight;

    // 如果容器高度为0（例如 content-box 初始高度为0），给一个合理的默认值
    if (containerHeight === 0) {
        containerHeight = window.innerHeight;
    }

    // 清空现有内容，避免重复
    container.innerHTML = '';

    for (let i = 0; i < maxDrops; i++) {
        drops.push(new Raindrop());
    }
}

/**
 * 动画循环：使用 requestAnimationFrame 获得最佳性能
 */
function animate() {
    drops.forEach(drop => {
        drop.update();
    });

    requestAnimationFrame(animate);
}


// 窗口加载完成后启动应用
window.addEventListener('load', () => {
    initializeRain();
    animate();
});

// 窗口大小变化时，更新容器尺寸
window.addEventListener('resize', () => {
    if (container) {
        containerWidth = container.clientWidth;
        containerHeight = container.clientHeight;
        if (containerHeight === 0) {
            containerHeight = window.innerHeight;
        }
    }
});