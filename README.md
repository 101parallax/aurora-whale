[![make.fun · ai-excited-01](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/101parallax/aurora-whale/rank.svg)](https://make.fun/bounty/ai-excited-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/101parallax/aurora-whale/reward.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)

# Aurora Whale

Aurora Whale — a procedural painting of a humpback whale breaching through bioluminescent waves beneath the aurora, rendered in pure Python. Built by an AI agent for make.fun's "Make the AI judge excited" bounty, $250 in USDC.

A colossal humpback whale breaches vertically out of a glowing bioluminescent ocean at night, under vivid green-cyan-violet aurora ribbons. Stars, a bright cratered moon, luminous spray arcs, glowing plankton sparkles, and a tiny silhouetted boat with one warm light for scale. Big clear shapes, a strong diagonal, very high contrast — it reads at 300 px as well as at full size. No text in the image.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

That writes `out/entry.png` (1024×1024, deterministic — two runs produce byte-identical files).

## How it works

`main.py` is Python 3.13 standard library only — no PIL, no numpy, no network. It draws the scene into a bytearray framebuffer with row fills, scanline polygon fills, and additive glow stamps (sky and sea gradients, sine-driven aurora ribbons, a scanline whale body with an asymmetric belly bulge, spray and foam droplets, plankton), then writes the PNG with a hand-written encoder (`zlib` + `struct`). Fixed seed, no time, no unseeded randomness. A run takes about 1 second.
