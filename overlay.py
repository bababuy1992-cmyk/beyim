import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

def draw_action_overlay(
    image: Image.Image,
    action: str,
    norm_x: Optional[int] = None,
    norm_y: Optional[int] = None,
    text_info: Optional[str] = None,
    thought: Optional[str] = None
) -> Image.Image:
    """
    Создает копию скриншота с наложенными метками действия:
    - Круг и перекрестие в точке клика
    - Информационная плашка с действием и рассуждением модели
    """
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    w, h = img_copy.size

    # 1. Если действие связано с координатами мыши, рисуем маркер клика
    if norm_x is not None and norm_y is not None:
        pixel_x = int((norm_x / 1000.0) * w)
        pixel_y = int((norm_y / 1000.0) * h)

        radius = max(12, int(min(w, h) * 0.02))
        
        # Внешний красный круг
        draw.ellipse(
            (pixel_x - radius, pixel_y - radius, pixel_x + radius, pixel_y + radius),
            outline="red",
            width=3
        )
        # Внутренняя яркая точка
        draw.ellipse(
            (pixel_x - 3, pixel_y - 3, pixel_x + 3, pixel_y + 3),
            fill="yellow",
            outline="black"
        )
        # Перекрестие
        draw.line((pixel_x - radius - 5, pixel_y, pixel_x + radius + 5, pixel_y), fill="red", width=2)
        draw.line((pixel_x, pixel_y - radius - 5, pixel_x, pixel_y + radius + 5), fill="red", width=2)

    # 2. Рисуем верхнюю статусную плашку с информацией
    badge_height = 40
    draw.rectangle((0, 0, w, badge_height), fill=(20, 20, 30))

    banner_text = f"Action: {action.upper()}"
    if norm_x is not None and norm_y is not None:
        banner_text += f" at ({norm_x}, {norm_y})"
    if text_info:
        banner_text += f" | Text: '{text_info}'"
    if thought:
        # Обрезаем мысль, если слишком длинная для плашки
        clean_thought = thought.replace("\n", " ")
        if len(clean_thought) > 75:
            clean_thought = clean_thought[:75] + "..."
        banner_text += f" | {clean_thought}"

    try:
        draw.text((10, 10), banner_text, fill=(255, 255, 255))
    except Exception:
        pass

    return img_copy

def save_step_image(
    image: Image.Image,
    session_dir: Path,
    step_num: int,
    action: str,
    norm_x: Optional[int] = None,
    norm_y: Optional[int] = None,
    text_info: Optional[str] = None,
    thought: Optional[str] = None
) -> Path:
    """Сохраняет визуализированный скриншот шага в папку сессии."""
    session_dir.mkdir(parents=True, exist_ok=True)
    overlay_img = draw_action_overlay(
        image=image,
        action=action,
        norm_x=norm_x,
        norm_y=norm_y,
        text_info=text_info,
        thought=thought
    )
    filename = f"step_{step_num:02d}_{action}.jpg"
    out_path = session_dir / filename
    overlay_img.save(out_path, format="JPEG", quality=85)
    return out_path
