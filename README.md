# animate

A Claude skill for making short animated videos with sound, made by drawing every frame in Python and muxing the audio with ffmpeg.

Good for stick figure fights, car crashes, runners, bouncing balls, and other simple scenes. No animation software needed, just Python and ffmpeg.

## What's in here

- `animate/SKILL.md`: the skill file Claude loads. Lists the steps: check tools, draw frames with PIL, generate sound with the wave module, mux with ffmpeg, verify the audio levels, send the mp4.
- `examples/car_moon.py`: a full working example. A car bounces, crashes into a wall, and launches to the moon, with sound effects. Use it as a reference for the frame loop, keyframe-style movement, and audio helpers.

## Requirements

- Python 3
- Pillow (`pip install pillow`)
- ffmpeg on your PATH (with libx264 and aac support)

## Install as a Claude skill

Copy the `animate/` folder into your skills directory, then Claude can load it with the Skill tool.

## Run the example

```
python3 examples/car_moon.py
```

It writes `car_moon_silent.mp4`, `car_moon.wav`, and `car_moon_with_sound.mp4` to the folder set in the script's `SCRATCH` variable. Change that path before running, since the example points at a sandbox folder.

## Tips

- 640x360 at 30 fps renders quickly for clips up to about 15 seconds.
- Check the final audio with `ffmpeg -i file.mp4 -af volumedetect -vn -f null -`. If max volume sits at 0 dB, lower the effect amplitudes so it doesn't clip.
- Use a seeded `random.Random(seed)` so the output is the same every run.

## License

MIT
