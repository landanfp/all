import asyncio
import os

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    position_map = {
        "top_right": "main_w-overlay_w-10:10",
        "top_center": "(main_w-overlay_w)/2:10",
        "top_left": "10:10",
        "center_right": "main_w-overlay_w-10:(main_h-overlay_h)/2",
        "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "center_left": "10:(main_h-overlay_h)/2",
        "bottom_right": "main_w-overlay_w-10:main_h-overlay_h-10",
        "bottom_center": "(main_w-overlay_w)/2:main_h-overlay_h-10",
        "bottom_left": "10:main_h-overlay_h-10"
    }

    drawtext = (
        f"drawtext=text='{text}':fontcolor=white:fontsize=h*{size_percent}/100:"
        f"x={position_map[position]}:y=(if(y,y,0))"
    )

    cmd = f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" -codec:a copy \"{output_path}\" -y"
    process = await asyncio.create_subprocess_shell(cmd)
    await process.communicate()

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    position_map = {
        "top_right": "main_w-overlay_w-10:10",
        "top_center": "(main_w-overlay_w)/2:10",
        "top_left": "10:10",
        "center_right": "main_w-overlay_w-10:(main_h-overlay_h)/2",
        "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "center_left": "10:(main_h-overlay_h)/2",
        "bottom_right": "main_w-overlay_w-10:main_h-overlay_h-10",
        "bottom_center": "(main_w-overlay_w)/2:main_h-overlay_h-10",
        "bottom_left": "10:main_h-overlay_h-10"
    }

    cmd = (
        f"ffmpeg -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"[1]scale=iw*{size_percent/100}:ih*{size_percent/100}[wm];[0][wm]overlay={position_map[position]}\" "
        f"-codec:a copy \"{output_path}\" -y"
    )
    process = await asyncio.create_subprocess_shell(cmd)
    await process.communicate()
