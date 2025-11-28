import os
from PIL import Image
import math

def create_uniform_spritesheet(frames_dir, output_filepath, cols=8, target_size=(150, 150)):
    """
    将目录中的所有 PNG 帧统一缩放为目标尺寸，然后合并为一张精灵表。

    Args:
        frames_dir (str): 包含单帧 PNG 图片的目录。
        output_filepath (str): 输出精灵表的路径。
        cols (int): 精灵表中的列数。
        target_size (tuple): 目标帧尺寸 (宽度, 高度)。
    """
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    if not frame_files:
        print(f"错误：在 {frames_dir} 中未找到任何 PNG 帧。")
        return

    scaled_frames = []

    # 获取目标宽高
    UNIFORM_FRAME_WIDTH, UNIFORM_FRAME_HEIGHT = target_size

    print(f"第一阶段：加载并统一缩放帧到 {UNIFORM_FRAME_WIDTH}x{UNIFORM_FRAME_HEIGHT}...")
    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_file)
        with Image.open(frame_path) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # 🌟 关键修改：直接缩放图像 🌟
            # Image.Resampling.LANCZOS 提供高质量的缩放效果
            scaled_img = img.resize(target_size, Image.Resampling.LANCZOS)
            scaled_frames.append(scaled_img)

    if not scaled_frames:
        print("没有找到有效的帧。")
        return

    num_frames = len(scaled_frames)
    rows = math.ceil(num_frames / cols)

    spritesheet_width = cols * UNIFORM_FRAME_WIDTH
    spritesheet_height = rows * UNIFORM_FRAME_HEIGHT

    spritesheet = Image.new('RGBA', (spritesheet_width, spritesheet_height), (0, 0, 0, 0))

    print(f"第二阶段：创建统一帧尺寸的精灵表: {num_frames} 帧，布局 {rows} 行 x {cols} 列，"
          f"统一帧尺寸 {UNIFORM_FRAME_WIDTH}x{UNIFORM_FRAME_HEIGHT}，总尺寸 {spritesheet_width}x{spritesheet_height}")

    for i, scaled_img in enumerate(scaled_frames):
        row = i // cols
        col = i % cols

        # 计算在精灵表上的粘贴位置 (直接粘贴，因为尺寸已统一)
        paste_x = col * UNIFORM_FRAME_WIDTH
        paste_y = row * UNIFORM_FRAME_HEIGHT

        spritesheet.paste(scaled_img, (paste_x, paste_y))

    spritesheet.save(output_filepath)
    print(f"✅ 成功创建统一尺寸的精灵表并保存到：{output_filepath}")


if __name__ == "__main__":
    # 🌟 在这里设定您的目标尺寸 🌟
    TARGET_SIZE = (350, 350)  # W x H

    FRAMES_FOLDER = "../extracted_sprites/upset"
    OUTPUT_SPRITESHEET = "../assets/upset.png"
    SPRITESHEET_COLS = 8

    create_uniform_spritesheet(FRAMES_FOLDER, OUTPUT_SPRITESHEET, cols=SPRITESHEET_COLS, target_size=TARGET_SIZE)