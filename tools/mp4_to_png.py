import cv2
import numpy as np
import os


def extract_spritesheet_with_alpha_mask(video_path, output_dir, frame_skip=1, tolerance=30):
    """
    從白色背景的影片中提取帶有透明背景的 PNG 幀。

    Args:
        video_path (str): 輸入 MP4 檔案的路徑。
        output_dir (str): 輸出 PNG 檔案的目錄。
        frame_skip (int): 每隔多少幀提取一次 (1 表示提取所有幀)。
        tolerance (int): 顏色容忍度。值越大，越多的白色會被視為透明 (例如：30)。
    """
    # 確保輸出目錄存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"錯誤：無法打開影片文件 {video_path}")
        return

    frame_count = 0
    extracted_count = 0

    # 定義目標背景色：純白色 (BGR 格式，因為 OpenCV 默認使用 BGR)
    target_color = np.array([255, 255, 255], dtype=np.uint8)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_skip == 0:
            # --- 核心摳像邏輯 ---

            # 1. 計算當前幀的每個像素與目標白色的顏色距離
            # np.abs 確保所有通道距離都是正值
            diff = np.abs(frame.astype(np.int32) - target_color.astype(np.int32))

            # 2. 計算總距離（所有 B, G, R 通道的距離之和的平均）
            # 或者使用每個像素最大的顏色差異 (max_diff)
            max_diff = np.max(diff, axis=2)

            # 3. 創建 Alpha Mask (掩碼)：
            # 如果 max_diff < tolerance (顏色接近白色)，則 Alpha 應為 0 (透明)。
            # 如果 max_diff >= tolerance，則 Alpha 應為 255 (不透明)。
            # 這裡我們使用一個平滑過渡（可選，更高級）：

            # 簡單的二值化透明度 (推薦用於您的場景)
            alpha_mask = np.where(max_diff < tolerance, 0, 255).astype(np.uint8)

            # --- 合併 Alpha 通道 ---

            # 4. 將 BGR 圖像轉換為 BGRA 圖像
            bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

            # 5. 將計算出的 Alpha Mask 應用到 BGRA 圖像的第四個通道 (Alpha 通道)
            bgra[:, :, 3] = alpha_mask

            # --- 輸出文件 ---

            output_filename = os.path.join(output_dir, f"frame_{extracted_count:04d}.png")
            cv2.imwrite(output_filename, bgra)

            extracted_count += 1

        frame_count += 1

    cap.release()
    print(f"成功從影片中提取了 {extracted_count} 幀，並保存到 {output_dir}")


if __name__ == "__main__":
    # 設置您的 MP4 影片路徑
    VIDEO_FILE = "../upset.mp4"
    # 設置輸出目錄
    OUTPUT_FOLDER = "../extracted_sprites/upset"
    # 顏色容忍度：需要根據您的影片調整。
    # 角色邊緣的白色殘留 (噪點) 越少，這個值可以設置得越高。
    # 建議從 20-30 開始測試。
    COLOR_TOLERANCE = 30

    extract_spritesheet_with_alpha_mask(VIDEO_FILE, OUTPUT_FOLDER, tolerance=COLOR_TOLERANCE)