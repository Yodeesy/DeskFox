// ripple.js - 专注于局部霓虹波纹

const RIPPLE_CONTAINER_ID = 'decBox';
const rippleColors = ['#ff00ff', '#00ffff', '#00ff80', '#ff8000', '#8000ff'];

function createRipple() {
    const container = document.getElementById(RIPPLE_CONTAINER_ID);
    if (!container) return;

    // 获取容器的内部尺寸 (clientWidth/Height)
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    // 只有当容器有明确尺寸时才生成波纹
    if (containerHeight === 0 || containerWidth === 0) return;

    const ripple = document.createElement('div');
    ripple.classList.add('ripple', 'neon-glow'); // 确保添加 neon-glow

    const size = Math.random() * 79 + 79;
    const duration = Math.random() * 3 + 2;
    const color = rippleColors[Math.floor(Math.random() * rippleColors.length)];

    // 随机中心点 (在容器内部)
    const centerX = Math.random() * containerWidth;
    const centerY = Math.random() * containerHeight;

    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;
    ripple.style.backgroundColor = color;
    ripple.style.color = color;

    // 核心定位：将波纹的中心对准 (centerX, centerY)
    ripple.style.left = `${centerX - size / 2}px`;
    ripple.style.top = `${centerY - size / 2}px`;

    // 应用动画
    ripple.style.animation = `ripple-spread ${duration}s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards`;

    container.appendChild(ripple);

    // 动画结束后移除
    setTimeout(() => {
        ripple.remove();
    }, duration * 1000);
}

// 持续创建波纹
setInterval(createRipple, 1900);