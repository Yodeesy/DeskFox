# Animation Pipeline Tools

## 两种工作流

### 工作流 A：骨骼部件动画（推荐，新方式）

适合制作新动画。将角色拆成部件（头、身体、尾巴等），用 JSON 定义运动，
工具自动合成每一帧并输出 spritesheet。

```
部件PNG (一次性拆分)  +  JSON 动画定义  →  [本工具]  →  spritesheet
```

**优点**：部件可复用，新动画只需写 JSON 关键帧，无需重新画每一帧。

**快速开始**：
```bash
# 1. 生成模板（含占位部件 + 示例动画）
python skeletal_to_spritesheet.py --init my_animations/fox

# 2. 预览动画
python skeletal_to_spritesheet.py my_animations/fox/idle.json --preview

# 3. 导出 spritesheet
python skeletal_to_spritesheet.py my_animations/fox/idle.json -o idle.png
```

然后：
1. 用自己的美术替换 `my_animations/fox/parts/` 下的占位 PNG
2. 编辑 `idle.json` 调整关键帧
3. `--preview` 实时预览，满意后导出 spritesheet
4. 在 `main.py` 的 `ANIMATION_CONFIG` 中添加

---

### 工作流 B：自动抠图管线（改进现有流程）

已有 MP4/逐帧 PNG 但需要去背景时使用。

```bash
# AI 自动去背景
python auto_bg_remove.py extracted_sprites/fishing/ output/clean_fishing/

# 合成 spritesheet
python frames_to_spritesheet.py output/clean_fishing/ fishing.png
```

---

## 动画 JSON 格式

```json
{
  "name": "idle",
  "canvas": {"width": 350, "height": 350},
  "duration_frames": 120,
  "framerate": 15,
  "parts": {
    "body": {
      "image": "parts/body.png",
      "anchor": [60, 80],
      "z": 1,
      "keyframes": [
        {"frame": 0,  "x": 0, "y": 0, "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
        {"frame": 60, "x": 0, "y": -8,"rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"},
        {"frame": 120,"x": 0, "y": 0, "rotation": 0,  "scale_x": 1.0, "scale_y": 1.0, "easing": "ease_in_out"}
      ]
    }
  }
}
```

**关键字段**：
- `anchor`：部件的锚点（相对部件图片左上角的偏移），旋转以此为中心
- `z`：渲染层级（数字越大越靠前）
- `keyframes`：至少 2 个，首尾 frame 应覆盖 [0, duration_frames]
- `easing`：缓动函数 — `linear` / `ease_in` / `ease_out` / `ease_in_out`
- `rotation`：角度制

**为现有代码生成配置提示**（`frames_to_spritesheet.py` 会自动打印）：
```python
"fishing": {
    "filepath": "assets/fishing.png",
    "frame_w": 350,
    "frame_h": 350,
    "total_frames": 120,
    "ranges": {"fishing": (0, 119)}
}
```

## 安装依赖

```bash
pip install pygame rembg pillow
```
