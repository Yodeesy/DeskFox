// time-theme.js

/**
 * 根据一天中的小时数计算背景亮度值 (0-255)。
 * 目标：12:00 (中午) -> 255 (白色)； 0:00/24:00 (午夜) -> 0 (黑色)。
 * 曲线：使用余弦函数模拟自然光线的变化，日出和日落的渐变速度更快。
 */
function updateBackgroundColor() {
    const now = new Date();
    const hours = now.getHours(); // 获取当前小时 (0-23)

    // 将小时数映射到 -PI 到 PI 的范围
    // 12点 -> 0
    // 0点/24点 -> PI 或 -PI
    // 映射公式: (hours - 12) * (Math.PI / 12)
    const angle = (hours - 12) * (Math.PI / 12);

    // 使用余弦函数计算亮度比例 (cos(x) 范围从 -1 到 1)
    // cos(0) = 1 (12点，最亮)
    // cos(PI) = -1 (0点/24点，最暗)
    const brightnessRatio = Math.cos(angle);

    // 将比例 (-1 到 1) 映射到灰度值 (0 到 255)
    // 1 -> 255 (白色)
    // -1 -> 0 (黑色)
    const brightnessValue = Math.round((brightnessRatio + 1) * 255 / 2);

    // 确保值在 0-255 范围内
    const finalBrightness = Math.max(0, Math.min(255, brightnessValue));

    // 将计算出的亮度值应用到 CSS 变量
    document.body.style.setProperty('--bg-color', finalBrightness);

    // 切换文本颜色
    const bodyStyle = document.body.style;
    const isDark = finalBrightness < 120; // 设定一个阈值，例如亮度小于120视为暗色模式

    if (isDark) {
            // 夜晚模式
            bodyStyle.setProperty('--color-primary', 'white');
            bodyStyle.setProperty('--color-navbar-bg', '#333');
            bodyStyle.setProperty('--color-footer-bg', '#1a1a1a');

            // 切换到暗色阴影，让导航栏融入背景
            bodyStyle.setProperty('--color-shadow-dynamic', 'var(--color-shadow-dark)');

           // 按钮背景变亮，按钮文本需要变黑以形成对比
            bodyStyle.setProperty('--color-btn-default', 'white');
            bodyStyle.setProperty('--color-btn-rec', '#6e987c'); // 按钮背景变浅
            bodyStyle.setProperty('--color-btn-text', 'black');  // 按钮文本变黑
        } else {
            // 白天模式
            bodyStyle.setProperty('--color-primary', '#333');
            bodyStyle.setProperty('--color-navbar-bg', 'white');
            bodyStyle.setProperty('--color-footer-bg', '#d8d6d6');

            // 切换到亮色阴影
            bodyStyle.setProperty('--color-shadow-dynamic', 'var(--color-shadow-light)');

            // 按钮背景变黑，按钮文本恢复白色
            bodyStyle.setProperty('--color-btn-default', 'black');
            bodyStyle.setProperty('--color-btn-rec', '#4c8e75');
            bodyStyle.setProperty('--color-btn-text', 'white');  // 按钮文本变白
        }
}

// 首次加载时更新背景
updateBackgroundColor();

// 每天的小时变化是平滑的，因此每 5 分钟更新一次就足够平滑且效率高
setInterval(updateBackgroundColor, 5 * 60 * 1000); // 5分钟更新一次