---
name: animate
description: Use when the user wants a short animated video (stick figures, shapes, simple scenes) with sound effects made by drawing frames in Python and muxing audio with ffmpeg.
---

# Animate

Make short animated mp4 videos by drawing every frame with PIL, generating sound effects with the wave module, and muxing both with ffmpeg. Works for stick figure fights, car crashes, runners, bouncing balls, and similar simple scenes.

## Steps

1. Check tools first. Run `python3 -c "import PIL"` and `which ffmpeg`. If ffmpeg is missing, tell the user it must be installed. If PIL is missing, run `pip install pillow --break-system-packages`.
2. Write a single script to the working directory, not a temp folder. Keep all outputs in the scratchpad or working directory and name the final file clearly (for example `fight_with_sound.mp4`).
3. Set the basics at the top of the script: width 640, height 360, fps 30, total seconds, sample rate 44100. Keep these the same unless the user asks for something else.
4. Video: open an ffmpeg process that reads raw RGB frames from stdin (`-f rawvideo -pix_fmt rgb24 -s WxH -r FPS -i -`), encodes with `libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart`. Loop over frame numbers, draw each frame with PIL, and write `img.tobytes()` to stdin. Close stdin and wait.
5. Animation: use keyframes (time, pose, x offset, y offset, rotation) and interpolate between them with a smoothstep. Use a sine or abs(sin) for bounces and hops. For flips, rotate all body points around the hip and raise the hip with a sin arc so the body clears the ground.
6. Audio: build a list of floats in the range -1 to 1, one per sample. Add effects at exact times: noise bursts with exponential decay for impacts and footsteps, falling sine sweeps for thuds and booms, short decaying blips for boinks, rising noise for whooshes, and short sine tones for chimes. Clamp, scale to int16, and write with the wave module (mono, 16-bit).
7. Mux: run `ffmpeg -y -i silent.mp4 -i audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -shortest final.mp4`.
8. Verify: run ffprobe for stream types and duration. Run `ffmpeg -i final.mp4 -af volumedetect -vn -f null -` and check mean and max volume (max near 0 dB may mean clipping, so lower the effect amplitudes). Optionally build a contact sheet with `fps=1,scale=320:-1,tile=5x2` and look at it to confirm the poses and text.
9. Send the final mp4 to the user with SendUserFile. Say the length, resolution, and fps, and list the sound effects.

## Tips

- Keep the render cheap: 30 fps at 640x360 renders quickly for clips up to about 15 seconds. Longer clips need a background run or lower fps.
- Python loops over sample data are slow. Keep audio generation to effects that fire at specific times, not per-sample heavy math.
- Use seeded random (`random.Random(seed)`) so the output is repeatable.
- Bash calls time out at 10 minutes, so split very long videos into chunks and stitch them with ffmpeg concat.
- If a hit should shake the screen, draw the frame, then paste it onto a fresh image at a small random offset.
