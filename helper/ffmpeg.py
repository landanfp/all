import asyncio

async def add_hardsub(input_video, input_subtitle, output_video):
    # Using ultrafast preset and 1 thread to minimize RAM usage
    cmd = f'ffmpeg -y -i "{input_video}" -vf subtitles="{input_subtitle}":force_style="Fontsize=24,PrimaryColour=&HFFFFFF&" -preset ultrafast -threads 1 -f mp4 "{output_video}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.communicate()