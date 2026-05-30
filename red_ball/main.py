#!/usr/bin/env python3
"""Red Ball — rolling-ball platformer
Run: python main.py
Web: python -m pygbag --build red_ball
"""
import pygame, math, sys, os, random, asyncio

try:
    import android
    _ANDROID = True
except ImportError:
    _ANDROID = False

pygame.init()
SW, SH = 900, 600
if _ANDROID:
    _real_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen = pygame.Surface((SW, SH))
    _rw, _rh = _real_screen.get_size()
    _rscale = min(_rw / SW, _rh / SH)
    _rsw, _rsh = int(SW * _rscale), int(SH * _rscale)
    _rox = (_rw - _rsw) // 2
    _roy = (_rh - _rsh) // 2
else:
    _real_screen = None
    _rw = _rh = _rscale = _rsw = _rsh = _rox = _roy = 0
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("Red Ball")

clock  = pygame.time.Clock()

# Touch state (Android)
_touch_left    = False
_touch_right   = False
_touch_jump    = False
_touch_fingers = {}

def _finger_to_game(fx, fy):
    if _ANDROID:
        return (fx * _rw - _rox) / max(1, _rscale), (fy * _rh - _roy) / max(1, _rscale)
    return fx * SW, fy * SH

def _update_touch_state():
    global _touch_left, _touch_right, _touch_jump
    _touch_left = _touch_right = _touch_jump = False
    for gx, gy in _touch_fingers.values():
        if gy > SH * 0.55:
            if gx < SW * 0.30:   _touch_left  = True
            elif gx < SW * 0.65: _touch_right = True
            else:                  _touch_jump  = True

FPS = 60

# ── Physics ───────────────────────────────────────────────────────────────────
GRAV     = 0.58
JUMP_V   = -13.2
MAX_FALL = 16.0
H_ACC    = 0.90
FRIC     = 0.83
MAX_HS   = 6.5
BR       = 18   # ball radius (also half-box side)
COYOTE   = 7    # coyote-time frames
JBUF     = 8    # jump-buffer frames

# ── Colors ────────────────────────────────────────────────────────────────────
SKY    = (112, 170, 228)
GND    = (78, 148, 56)
DIRT   = (98, 66, 32)
PLAT   = (82, 128, 196)
PLAT2  = (62, 102, 158)
MOVC   = (200, 140, 58)
MOVC2  = (158, 108, 38)
BALLF  = (222, 36, 36)
BALLD  = (158, 14, 14)
BALLH  = (255, 92, 92)
ENE    = (24, 22, 28)
ENE2   = (54, 50, 60)
ENEEYE = (200, 48, 48)
STARY  = (255, 215, 0)
STARO  = (255, 168, 0)
SPKC   = (178, 178, 188)
FLAGC  = (255, 86, 0)
FLAGP  = (88, 48, 20)
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
GRAY   = (132, 132, 142)
DGRAY  = (42, 42, 52)
DARK   = (10, 12, 20)
RED    = (222, 44, 40)
GREEN  = (56, 196, 56)
CYAN   = (0, 200, 255)
YELLOW = (255, 220, 0)
ORANGE = (255, 122, 0)

# ── Sounds (procedural) ───────────────────────────────────────────────────────
class Snd:
    def __init__(self):
        self._ok = False
        try:
            pygame.mixer.init(44100, -16, 1, 512)
            self._ok = True
            self._cache = {}
        except Exception:
            pass

    def _gen(self, key, fn):
        if not self._ok: return None
        if key not in self._cache:
            try: self._cache[key] = fn()
            except Exception: return None
        return self._cache[key]

    @staticmethod
    def _buf(samples):
        import array
        buf = array.array('h', samples)
        snd = pygame.sndarray.make_sound(pygame.surfarray.make_surface(
            pygame.surfarray.array2d(pygame.Surface((1,1)))))
        snd = pygame.mixer.Sound(buffer=buf.tobytes())
        return snd

    def _tone(self, freq=440, dur=0.12, vol=0.4, env=0.02):
        import array, struct
        SR = 44100
        n  = int(SR * dur)
        ev = int(SR * env)
        data = []
        for i in range(n):
            t   = i / SR
            amp = math.sin(2 * math.pi * freq * t)
            fade = min(i, ev) / ev * max(0, min(1, (n - i) / ev))
            data.append(int(amp * fade * 32000 * vol))
        try:
            snd = pygame.mixer.Sound(buffer=bytes(struct.pack(f'{len(data)}h', *data)))
            return snd
        except Exception:
            return None

    def _noise(self, dur=0.08, vol=0.3, lo=200, hi=800):
        import struct
        SR  = 44100
        n   = int(SR * dur)
        ev  = max(1, int(SR * 0.01))
        data = []
        for i in range(n):
            amp  = random.uniform(-1, 1)
            fade = min(i, ev) / ev * max(0, (n - i) / max(1, n // 3))
            data.append(int(amp * fade * 32000 * vol))
        try:
            return pygame.mixer.Sound(buffer=bytes(struct.pack(f'{len(data)}h', *data)))
        except Exception:
            return None

    def play_jump(self):
        s = self._gen('jump', lambda: self._tone(300, 0.15, 0.5, 0.01))
        if s: s.play()

    def play_star(self):
        s = self._gen('star', lambda: self._tone(880, 0.12, 0.4, 0.01))
        if s: s.play()

    def play_stomp(self):
        s = self._gen('stomp', lambda: self._noise(0.12, 0.5))
        if s: s.play()

    def play_die(self):
        s = self._gen('die', lambda: self._tone(180, 0.4, 0.6, 0.05))
        if s: s.play()

    def play_win(self):
        s = self._gen('win', lambda: self._tone(660, 0.35, 0.5, 0.01))
        if s: s.play()

    def play_click(self):
        s = self._gen('click', lambda: self._tone(500, 0.06, 0.3, 0.005))
        if s: s.play()

snd = Snd()

# ── Particles ─────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, col):
        self.x   = x + random.uniform(-8, 8)
        self.y   = y + random.uniform(-8, 8)
        self.vx  = random.uniform(-3, 3)
        self.vy  = random.uniform(-5, -1)
        self.col = col
        self.r   = random.randint(3, 7)
        self.life = random.randint(20, 35)
        self.max_life = self.life

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.25
        self.life -= 1

    def draw(self, surf, cx):
        if self.life <= 0: return
        a = self.life / self.max_life
        col = tuple(int(c * a) for c in self.col)
        pygame.draw.circle(surf, col, (int(self.x - cx), int(self.y)), max(1, int(self.r * a)))

# ── Level data ────────────────────────────────────────────────────────────────
# Each platform = pygame.Rect
# enemies  = list of [x, y, w, h, patrol_range, speed]
# stars    = list of [x, y]
# spikes   = list of (x, y, count, horiz)  count triangles in a row
# mplats   = list of [x, y, w, h, dx, dy, range]  moving platforms

LEVELS = [
  # ── Level 1 : Green Hills ─────────────────────────────────────────────────
  dict(
    name='Green Hills', bg=SKY, ww=3200,
    start=(70, 470),
    flag =(3100, 478),
    plats=[
      pygame.Rect(0,   500, 700,  100),   # ground A
      pygame.Rect(780, 500, 500,  100),   # ground B (gap 80px)
      pygame.Rect(1380,500, 500,  100),   # ground C
      pygame.Rect(1980,500, 400,  100),   # ground D
      pygame.Rect(2480,500, 720,  100),   # ground E to end

      pygame.Rect(250, 420, 140, 20),     # low step
      pygame.Rect(860, 400, 140, 20),     # over gap
      pygame.Rect(1200,400, 140, 20),
      pygame.Rect(1550,380, 140, 20),
      pygame.Rect(1700,420, 140, 20),
      pygame.Rect(2080,420, 140, 20),
      pygame.Rect(2300,380, 140, 20),
      pygame.Rect(2600,420, 140, 20),
      pygame.Rect(2800,380, 140, 20),
      pygame.Rect(3000,420, 140, 20),
    ],
    mplats=[],
    enemies=[
      [500,  458, 56, 44, 140, 1.2],
      [1450, 458, 56, 44, 120, 1.2],
      [2100, 458, 56, 44, 120, 1.4],
    ],
    stars=[
      [120,  470], [300,  385], [870,  365], [1210, 365],
      [1560, 345], [2100, 385], [2620, 385], [3010, 385],
    ],
    spikes=[],
  ),

  # ── Level 2 : Blue Bridges ────────────────────────────────────────────────
  dict(
    name='Blue Bridges', bg=(90, 140, 210), ww=3800,
    start=(70, 470),
    flag =(3680, 478),
    plats=[
      pygame.Rect(0,   500, 500, 100),
      pygame.Rect(600, 500, 300, 100),
      pygame.Rect(1000,500, 300, 100),
      pygame.Rect(1400,500, 300, 100),
      pygame.Rect(1800,500, 500, 100),
      pygame.Rect(2400,500, 300, 100),
      pygame.Rect(2800,500, 600, 100),
      pygame.Rect(3500,500, 300, 100),

      pygame.Rect(200, 400, 120, 20),
      pygame.Rect(620, 400, 120, 20),
      pygame.Rect(900, 360, 120, 20),
      pygame.Rect(1100,400, 120, 20),
      pygame.Rect(1420,380, 120, 20),
      pygame.Rect(1620,340, 120, 20),
      pygame.Rect(1820,380, 120, 20),
      pygame.Rect(2050,340, 120, 20),
      pygame.Rect(2300,380, 120, 20),  # before big gap
      pygame.Rect(2650,400, 120, 20),
      pygame.Rect(2950,380, 120, 20),
      pygame.Rect(3200,340, 120, 20),
      pygame.Rect(3400,380, 120, 20),
      pygame.Rect(3600,400, 120, 20),
    ],
    mplats=[
      [1840, 440, 120, 18, 2.0, 0, 160],   # moves left-right 160px
      [2450, 420, 120, 18, 0, 2.2, 120],   # moves up-down
    ],
    enemies=[
      [300,  458, 56, 44, 140, 1.4],
      [700,  458, 56, 44, 100, 1.4],
      [1050, 458, 56, 44, 120, 1.4],
      [2000, 458, 56, 44, 140, 1.6],
      [3000, 458, 56, 44, 160, 1.6],
    ],
    stars=[
      [120,470],[620,365],[910,325],[1100,365],[1430,345],
      [1630,305],[2060,305],[2310,345],[2660,365],[3210,305],[3510,345],
    ],
    spikes=[(1350, 500, 2, True)],
  ),

  # ── Level 3 : Rocky Heights ───────────────────────────────────────────────
  dict(
    name='Rocky Heights', bg=(80, 120, 175), ww=4200,
    start=(70, 470),
    flag =(4080, 478),
    plats=[
      pygame.Rect(0,   500, 600, 100),
      pygame.Rect(700, 500, 400, 100),
      pygame.Rect(1200,500, 300, 100),
      pygame.Rect(1600,500, 400, 100),
      pygame.Rect(2100,500, 300, 100),
      pygame.Rect(2600,500, 600, 100),
      pygame.Rect(3300,500, 500, 100),
      pygame.Rect(3900,500, 300, 100),

      # Low platforms
      pygame.Rect(600, 420, 120, 20),
      pygame.Rect(820, 380, 120, 20),
      # Mid
      pygame.Rect(1100,420, 120, 20),
      pygame.Rect(1280,360, 120, 20),
      pygame.Rect(1480,300, 140, 20),
      pygame.Rect(1680,340, 140, 20),
      pygame.Rect(1880,300, 140, 20),
      pygame.Rect(2080,260, 140, 20),
      # Coming down
      pygame.Rect(2300,300, 120, 20),
      pygame.Rect(2480,340, 120, 20),
      pygame.Rect(2700,380, 120, 20),
      # Spiky section
      pygame.Rect(3000,380, 120, 20),
      pygame.Rect(3200,340, 120, 20),
      pygame.Rect(3400,380, 120, 20),
      pygame.Rect(3600,420, 120, 20),
      pygame.Rect(3800,380, 120, 20),
      pygame.Rect(4000,420, 120, 20),
    ],
    mplats=[
      [1500, 460, 120, 18, 2.5, 0, 200],
      [2200, 420, 120, 18, 0, 2.5, 160],
      [2800, 450, 120, 18, 3.0, 0, 240],
      [3700, 440, 120, 18, 2.0, 0, 180],
    ],
    enemies=[
      [400, 458, 56, 44, 150, 1.4],
      [900, 458, 56, 44, 120, 1.4],
      [1400,458, 56, 44, 120, 1.6],
      [2200,458, 56, 44, 140, 1.6],
      [3100,458, 56, 44, 140, 1.8],
      [3600,458, 56, 44, 160, 1.8],
    ],
    stars=[
      [100,470],[620,385],[840,345],[1110,385],[1300,325],
      [1500,265],[1900,265],[2100,225],[2490,305],[2710,345],
      [3010,345],[3210,305],[3410,345],[3810,345],[4010,385],
    ],
    spikes=[
      (700, 500, 2, True),
      (1900, 500, 3, True),
      (2800, 500, 2, True),
    ],
  ),

  # ── Level 4 : Danger Zone ─────────────────────────────────────────────────
  dict(
    name='Danger Zone', bg=(75, 55, 90), ww=4600,
    start=(70, 470),
    flag =(4480, 478),
    plats=[
      pygame.Rect(0,   500, 500, 100),
      pygame.Rect(600, 500, 300, 100),
      pygame.Rect(1100,500, 300, 100),
      pygame.Rect(1600,500, 300, 100),
      pygame.Rect(2100,500, 400, 100),
      pygame.Rect(2700,500, 300, 100),
      pygame.Rect(3200,500, 400, 100),
      pygame.Rect(3800,500, 400, 100),
      pygame.Rect(4300,500, 300, 100),

      pygame.Rect(500, 420, 120, 20),
      pygame.Rect(750, 380, 120, 20),
      pygame.Rect(1000,340, 140, 20),
      pygame.Rect(1200,380, 120, 20),
      pygame.Rect(1450,420, 120, 20),
      pygame.Rect(1700,360, 140, 20),
      pygame.Rect(1950,300, 160, 20),
      pygame.Rect(2200,340, 140, 20),
      pygame.Rect(2450,380, 120, 20),
      pygame.Rect(2800,360, 140, 20),
      pygame.Rect(3050,300, 140, 20),
      pygame.Rect(3300,340, 140, 20),
      pygame.Rect(3550,300, 140, 20),
      pygame.Rect(3800,340, 140, 20),
      pygame.Rect(4050,380, 120, 20),
      pygame.Rect(4250,420, 120, 20),
    ],
    mplats=[
      [600,  450, 110, 18, 2.5, 0, 180],
      [1300, 420, 110, 18, 0, 3.0, 160],
      [2000, 440, 110, 18, 3.0, 0, 200],
      [2800, 450, 110, 18, 2.5, 2.5, 150],
      [3400, 430, 110, 18, 0, 3.0, 180],
      [4000, 450, 110, 18, 2.0, 0, 200],
    ],
    enemies=[
      [300,  458, 56, 44, 120, 1.6],
      [800,  458, 56, 44, 100, 1.6],
      [1300, 458, 56, 44, 120, 1.8],
      [1800, 458, 56, 44, 120, 1.8],
      [2300, 458, 56, 44, 140, 2.0],
      [3000, 458, 56, 44, 140, 2.0],
      [3600, 458, 56, 44, 160, 2.0],
      [4200, 458, 56, 44, 120, 2.2],
    ],
    stars=[
      [100,470],[510,385],[760,345],[1010,305],[1210,345],
      [1460,385],[1710,325],[1960,265],[2210,305],[2460,345],
      [2810,325],[3060,265],[3310,305],[3560,265],[3810,305],
      [4060,345],[4260,385],
    ],
    spikes=[
      (550,  500, 2, True),
      (1000, 500, 3, True),
      (1600, 500, 2, True),
      (2300, 500, 3, True),
      (3000, 500, 3, True),
      (3700, 500, 2, True),
    ],
  ),

  # ── Level 5 : Final Castle ────────────────────────────────────────────────
  dict(
    name='Final Castle', bg=(55, 35, 65), ww=5200,
    start=(70, 470),
    flag =(5080, 478),
    plats=[
      pygame.Rect(0,   500, 450, 100),
      pygame.Rect(550, 500, 300, 100),
      pygame.Rect(1050,500, 300, 100),
      pygame.Rect(1550,500, 300, 100),
      pygame.Rect(2100,500, 300, 100),
      pygame.Rect(2700,500, 300, 100),
      pygame.Rect(3300,500, 300, 100),
      pygame.Rect(3900,500, 300, 100),
      pygame.Rect(4500,500, 400, 100),
      pygame.Rect(4950,500, 250, 100),

      pygame.Rect(400, 420, 130, 20),
      pygame.Rect(700, 380, 130, 20),
      pygame.Rect(950, 340, 130, 20),
      pygame.Rect(1200,300, 130, 20),
      pygame.Rect(1450,260, 130, 20),
      pygame.Rect(1700,300, 130, 20),
      pygame.Rect(1950,340, 130, 20),
      pygame.Rect(2200,300, 130, 20),
      pygame.Rect(2450,260, 130, 20),
      pygame.Rect(2700,300, 130, 20),
      pygame.Rect(2950,340, 130, 20),
      pygame.Rect(3200,300, 130, 20),
      pygame.Rect(3450,260, 130, 20),
      pygame.Rect(3700,300, 130, 20),
      pygame.Rect(3950,340, 130, 20),
      pygame.Rect(4200,380, 130, 20),
      pygame.Rect(4450,420, 130, 20),
      pygame.Rect(4700,380, 130, 20),
      pygame.Rect(4950,420, 130, 20),
    ],
    mplats=[
      [550,  460, 110, 18, 3.0, 0, 180],
      [1100, 440, 110, 18, 0, 3.5, 180],
      [1700, 460, 110, 18, 3.5, 0, 200],
      [2300, 440, 110, 18, 3.0, 3.0, 160],
      [2900, 450, 110, 18, 3.5, 0, 200],
      [3500, 450, 110, 18, 0, 3.5, 180],
      [4100, 450, 110, 18, 3.0, 0, 200],
      [4700, 450, 110, 18, 3.5, 3.5, 160],
    ],
    enemies=[
      [250, 458, 56, 44, 100, 1.8],
      [650, 458, 56, 44, 100, 1.8],
      [1100,458, 56, 44, 120, 2.0],
      [1650,458, 56, 44, 120, 2.0],
      [2250,458, 56, 44, 120, 2.2],
      [2850,458, 56, 44, 140, 2.2],
      [3450,458, 56, 44, 140, 2.4],
      [4050,458, 56, 44, 140, 2.4],
      [4650,458, 56, 44, 120, 2.6],
    ],
    stars=[
      [100,470],[410,385],[710,345],[960,305],[1210,265],
      [1460,225],[1710,265],[1960,305],[2210,265],[2460,225],
      [2710,265],[2960,305],[3210,265],[3460,225],[3710,265],
      [3960,305],[4210,345],[4460,385],[4710,345],[4960,385],
    ],
    spikes=[
      (500,  500, 2, True),
      (1000, 500, 3, True),
      (1500, 500, 2, True),
      (2050, 500, 3, True),
      (2650, 500, 3, True),
      (3250, 500, 3, True),
      (3850, 500, 2, True),
      (4450, 500, 2, True),
    ],
  ),
]

# ── Helper: draw text centred ─────────────────────────────────────────────────
def ctr(surf, text, y, col=WHITE, size=24):
    f = pygame.font.SysFont('monospace', size, bold=True)
    t = f.render(text, True, col)
    surf.blit(t, t.get_rect(center=(SW//2, y)))

def ctr_s(text, size=24, col=WHITE, bold=True):
    f = pygame.font.SysFont('monospace', size, bold=bold)
    return f.render(text, True, col)

def draw_rounded_rect(surf, col, rect, r=8, width=0):
    pygame.draw.rect(surf, col, rect, width, border_radius=r)

# ── Draw sky gradient ─────────────────────────────────────────────────────────
def draw_sky(surf, bg):
    top = tuple(max(0, c - 40) for c in bg)
    for y in range(SH):
        t = y / SH
        col = tuple(int(top[i] + (bg[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surf, col, (0, y), (SW, y))

# ── Spike drawing ─────────────────────────────────────────────────────────────
def draw_spikes(surf, spikes, cx):
    TW = 24
    for (sx, sy, count, horiz) in spikes:
        for i in range(count):
            if horiz:
                x0 = sx - cx + i * TW
                pts = [(x0, sy), (x0 + TW, sy), (x0 + TW//2, sy - 22)]
            else:
                y0 = sy + i * TW
                pts = [(sx - cx, y0), (sx - cx, y0 + TW), (sx - cx + 22, y0 + TW//2)]
            pygame.draw.polygon(surf, SPKC, pts)

# ── Ball ──────────────────────────────────────────────────────────────────────
class Ball:
    def __init__(self, x, y):
        self.reset(x, y)

    def reset(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.angle   = 0.0
        self.on_gnd  = False
        self.coyote  = 0
        self.jbuf    = 0
        self.alive   = True
        self.squash  = 1.0   # vertical squash on landing
        self.squash_v= 0.0
        self.has_mp  = None  # moving platform we're standing on

    def rect(self):
        return pygame.Rect(self.x - BR, self.y - BR, BR*2, BR*2)

    def jump_press(self):
        self.jbuf = JBUF

    def _resolve_plats(self, plats):
        """Separate X then Y collision against static rects."""
        r = self.rect()
        # X
        for p in plats:
            if r.colliderect(p):
                if self.vx > 0:
                    self.x = p.left - BR
                    self.vx = 0
                elif self.vx < 0:
                    self.x = p.right + BR
                    self.vx = 0
                r = self.rect()
        # Y
        self.on_gnd = False
        for p in plats:
            if r.colliderect(p):
                if self.vy > 0:
                    self.y = p.top - BR
                    self.vy = 0
                    self.on_gnd = True
                    if self.squash > 1.0:
                        self.squash   = 0.6
                        self.squash_v = 0.06
                elif self.vy < 0:
                    self.y = p.bottom + BR
                    self.vy = 0
                r = self.rect()

    def update(self, plats, mplats, keys):
        if not self.alive: return

        # Input (keyboard + touch)
        left  = keys[pygame.K_LEFT]  or keys[pygame.K_a]  or _touch_left
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]  or _touch_right

        if left:  self.vx -= H_ACC
        elif right: self.vx += H_ACC
        else:     self.vx *= FRIC

        self.vx = max(-MAX_HS, min(MAX_HS, self.vx))

        # Coyote + jump buffer
        if self.on_gnd: self.coyote = COYOTE
        else: self.coyote = max(0, self.coyote - 1)
        if self.jbuf > 0: self.jbuf -= 1

        if self.jbuf > 0 and self.coyote > 0:
            self.vy = JUMP_V
            self.coyote = 0
            self.jbuf   = 0
            snd.play_jump()

        # Gravity
        self.vy = min(self.vy + GRAV, MAX_FALL)

        # Move + collide with static platforms
        self.x += self.vx
        self.y += self.vy
        self._resolve_plats(plats)

        # Moving platforms
        self.has_mp = None
        for mp in mplats:
            mpv = mp.rect()
            # Carry if standing on top
            if abs((self.y + BR) - mpv.top) <= 6 and self.x > mpv.left - BR and self.x < mpv.right + BR:
                self.y = mpv.top - BR
                self.vy = 0
                self.on_gnd = True
                self.has_mp = mp
                self.x += mp.vx
                self.y += mp.vy
            elif self.rect().colliderect(mpv):
                if self.vy > 0 and self.y < mpv.centery:
                    self.y = mpv.top - BR
                    self.vy = 0
                    self.on_gnd = True
                    self.has_mp = mp
                elif self.vy < 0:
                    self.y = mpv.bottom + BR
                    self.vy = 0
                elif self.vx > 0:
                    self.x = mpv.left - BR; self.vx = 0
                else:
                    self.x = mpv.right + BR; self.vx = 0

        # Rolling
        self.angle += self.vx * 1.8

        # Squash
        self.squash   += self.squash_v
        self.squash_v *= 0.7
        if abs(self.squash - 1.0) < 0.01 and abs(self.squash_v) < 0.002:
            self.squash = 1.0; self.squash_v = 0.0
        self.squash = max(0.55, min(1.45, self.squash))

    def draw(self, surf, cx):
        if not self.alive: return
        x, y = int(self.x - cx), int(self.y)
        sq   = self.squash
        rw   = max(4, int(BR / sq))
        rh   = max(4, int(BR * sq))

        # Shadow
        pygame.draw.ellipse(surf, (0,0,0,60), (x - rw, y + rh - 4, rw*2, 8))

        # Ball surface with rotation
        bs = pygame.Surface((rw*2, rh*2), pygame.SRCALPHA)
        pygame.draw.ellipse(bs, BALLF, (0, 0, rw*2, rh*2))
        pygame.draw.ellipse(bs, BALLD, (0, 0, rw*2, rh*2), 3)

        # Rotation line
        ang = math.radians(self.angle)
        lx  = rw + math.cos(ang) * (rw - 4)
        ly  = rh + math.sin(ang) * (rh - 4)
        pygame.draw.line(bs, BALLD, (rw, rh), (int(lx), int(ly)), 3)

        # Highlight
        pygame.draw.ellipse(bs, BALLH, (rw//2 - 3, rh//2 - 3, rw//2, rh//2))

        surf.blit(bs, (x - rw, y - rh))

# ── Moving platform ───────────────────────────────────────────────────────────
class MovingPlatform:
    def __init__(self, cfg):
        self.ox, self.oy, self.w, self.h = cfg[0], cfg[1], cfg[2], cfg[3]
        self.dx, self.dy, self.rng = cfg[4], cfg[5], cfg[6]
        self.x, self.y = float(self.ox), float(self.oy)
        self.t = 0.0
        self.vx = self.vy = 0.0

    def update(self):
        self.t += 0.025
        px, py = self.x, self.y
        if self.dx != 0:
            self.x = self.ox + math.sin(self.t * self.dx) * self.rng / 2
        if self.dy != 0:
            self.y = self.oy + math.sin(self.t * self.dy) * self.rng / 2
        self.vx = self.x - px
        self.vy = self.y - py

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def draw(self, surf, cx):
        r = self.rect()
        pygame.draw.rect(surf, MOVC,  (r.x - cx, r.y, r.w, r.h), border_radius=6)
        pygame.draw.rect(surf, MOVC2, (r.x - cx, r.y, r.w, r.h), 2, border_radius=6)
        # Arrow hint
        ax = r.x - cx + r.w//2
        ay = r.y + r.h//2
        pygame.draw.polygon(surf, WHITE, [(ax-8,ay),(ax+8,ay),(ax,ay-7)])

# ── Enemy ─────────────────────────────────────────────────────────────────────
class Enemy:
    def __init__(self, cfg):
        self.sx  = cfg[0]
        self.x   = float(cfg[0])
        self.y   = float(cfg[1])
        self.w   = cfg[2]
        self.h   = cfg[3]
        self.rng = cfg[4]
        self.spd = cfg[5]
        self.dir = 1
        self.alive = True
        self.die_t  = 0
        self.walk_t = 0.0

    def update(self):
        if not self.alive:
            self.die_t -= 1; return
        self.x += self.spd * self.dir
        self.walk_t += self.spd
        if abs(self.x - self.sx) > self.rng / 2:
            self.dir *= -1

    def rect(self):
        return pygame.Rect(int(self.x - self.w//2), int(self.y - self.h), self.w, self.h)

    def draw(self, surf, cx):
        if not self.alive and self.die_t <= 0: return
        x = int(self.x - cx)
        y = int(self.y)
        a = max(0, min(255, self.die_t * 12)) if not self.alive else 255
        # Body
        r = pygame.Rect(x - self.w//2, y - self.h, self.w, self.h)
        pygame.draw.rect(surf, ENE,  r, border_radius=4)
        pygame.draw.rect(surf, ENE2, r, 2, border_radius=4)
        # Eyes
        ey = y - self.h + 10
        for ex in [x - 10, x + 5]:
            pygame.draw.circle(surf, WHITE, (ex, ey), 7)
            pygame.draw.circle(surf, ENE,   (ex + self.dir*2, ey + 2), 4)
            pygame.draw.circle(surf, ENEEYE,(ex + self.dir*2, ey + 2), 2)
        # Legs
        lt = math.sin(self.walk_t * 0.25)
        pygame.draw.line(surf, ENE2, (x - 8, y), (x - 8 + int(lt*6), y + 8), 4)
        pygame.draw.line(surf, ENE2, (x + 8, y), (x + 8 - int(lt*6), y + 8), 4)

# ── Star ──────────────────────────────────────────────────────────────────────
class Star:
    def __init__(self, cfg):
        self.x, self.y = float(cfg[0]), float(cfg[1])
        self.t = random.uniform(0, math.pi*2)
        self.alive = True

    def update(self):
        self.t += 0.06

    def rect(self):
        return pygame.Rect(int(self.x) - 12, int(self.y) - 12, 24, 24)

    def draw(self, surf, cx):
        if not self.alive: return
        x = int(self.x - cx)
        y = int(self.y + math.sin(self.t) * 4)
        r = 10 + math.sin(self.t * 2) * 1.5
        for i in range(5):
            a  = math.radians(i * 72 - 90)
            a2 = math.radians(i * 72 + 36 - 90)
            pts = [
                (x + math.cos(a) * r,   y + math.sin(a) * r),
                (x + math.cos(a2) * r/2.4, y + math.sin(a2) * r/2.4),
            ]
            if i == 0: outer = [pts[0]]
            else:
                outer.append(pts[0])
        # Simple 5-point star
        pts5 = []
        for i in range(10):
            ang = math.radians(i * 36 - 90)
            rad = r if i % 2 == 0 else r / 2.5
            pts5.append((x + math.cos(ang)*rad, y + math.sin(ang)*rad))
        pygame.draw.polygon(surf, STARY, pts5)
        pygame.draw.polygon(surf, STARO, pts5, 1)
        pygame.draw.circle(surf, WHITE, (x, y), 3)

# ── Flag (finish) ─────────────────────────────────────────────────────────────
class Flag:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.t = 0.0

    def update(self): self.t += 0.05

    def rect(self): return pygame.Rect(int(self.x) - 20, int(self.y) - 60, 40, 60)

    def draw(self, surf, cx):
        x = int(self.x - cx)
        y = int(self.y)
        # Pole
        pygame.draw.rect(surf, FLAGP, (x-3, y-80, 6, 80))
        # Flag wave
        pts = [(x+3, y-80)]
        for i in range(8):
            fx = x + 3 + i * 5
            fy = y - 80 + int(math.sin(self.t + i * 0.5) * 5)
            pts.append((fx, fy))
        pts += [(x+3, y-60)]
        pygame.draw.polygon(surf, FLAGC, pts)
        # Base
        pygame.draw.ellipse(surf, FLAGP, (x-14, y-8, 28, 10))

# ── Spike collision ───────────────────────────────────────────────────────────
def spike_rects(spikes):
    rects = []
    TW = 24
    for (sx, sy, count, horiz) in spikes:
        for i in range(count):
            if horiz:
                rects.append(pygame.Rect(sx + i*TW, sy - 18, TW, 18))
            else:
                rects.append(pygame.Rect(sx, sy + i*TW, 18, TW))
    return rects

# ── Camera ────────────────────────────────────────────────────────────────────
class Camera:
    def __init__(self):
        self.x = 0.0

    def update(self, ball_x, world_w):
        target = ball_x - SW * 0.35
        target = max(0, min(target, world_w - SW))
        self.x += (target - self.x) * 0.12

# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.font_big = pygame.font.SysFont('monospace', 52, bold=True)
        self.font_med = pygame.font.SysFont('monospace', 28, bold=True)
        self.font_sm  = pygame.font.SysFont('monospace', 18, bold=True)
        self.font_xs  = pygame.font.SysFont('monospace', 14)
        self._state   = 'menu'
        self._lv      = 0
        self._lives   = 3
        self._score   = 0
        self._hi      = self._load_hi()
        self._cam     = Camera()
        self._particles = []
        self._flash     = 0
        self._stars_got = 0
        self._stars_total = 0
        self._level_done  = False
        self._done_timer  = 0
        self._hover = ''
        self._menu_stars = [(random.uniform(0,SW), random.uniform(0,SH//2),
                             random.uniform(0.5,2.5)) for _ in range(60)]
        self._load_level(0)

    def _load_hi(self):
        try:
            p = os.path.join(os.path.dirname(__file__), 'save.json')
            with open(p) as f: return json.load(f).get('hi', 0)
        except Exception: return 0

    def _save_hi(self):
        try:
            p = os.path.join(os.path.dirname(__file__), 'save.json')
            d = {}
            try:
                with open(p) as f: d = json.load(f)
            except Exception: pass
            d['hi'] = self._hi
            with open(p, 'w') as f: json.dump(d, f)
        except Exception: pass

    def _load_level(self, idx):
        if idx >= len(LEVELS): return
        ld = LEVELS[idx]
        self._lv_data    = ld
        self._plats      = list(ld['plats'])
        self._mplats     = [MovingPlatform(c) for c in ld['mplats']]
        self._enemies    = [Enemy(c) for c in ld['enemies']]
        self._stars      = [Star(c) for c in ld['stars']]
        self._spikes     = ld['spikes']
        self._spike_rects= spike_rects(ld['spikes'])
        self._flag       = Flag(*ld['flag'])
        self._ball       = Ball(*ld['start'])
        self._cam.x      = 0.0
        self._particles  = []
        self._stars_got  = 0
        self._stars_total= len(ld['stars'])
        self._level_done = False
        self._done_timer = 0
        self._flash      = 0

    def _spawn_particles(self, x, y, col, n=12):
        for _ in range(n): self._particles.append(Particle(x, y, col))

    def _update_play(self, keys):
        mp = self._mplats
        for m in mp: m.update()

        all_plats = self._plats + [m.rect() for m in mp]
        self._ball.update(all_plats, mp, keys)

        # Stars
        br = self._ball.rect()
        for s in self._stars:
            if s.alive and br.colliderect(s.rect()):
                s.alive = False
                self._stars_got += 1
                self._score += 100
                self._spawn_particles(s.x, s.y, STARY, 8)
                snd.play_star()
            s.update()

        # Enemies
        for e in self._enemies:
            e.update()
            if not e.alive: continue
            er = e.rect()
            if br.colliderect(er):
                ball_bottom = self._ball.y + BR
                enemy_top   = e.y - e.h
                # Stomp check: ball moving down, bottom near enemy top
                if self._ball.vy > 0 and ball_bottom < e.y - e.h//2 + 6:
                    e.alive = False
                    e.die_t = 12
                    self._ball.vy = JUMP_V * 0.65
                    self._score += 200
                    self._spawn_particles(e.x, e.y - e.h//2, ENE2, 12)
                    snd.play_stomp()
                else:
                    self._die()
                    return

        # Spikes
        for sr in self._spike_rects:
            if br.colliderect(sr):
                self._die(); return

        # Fall off
        if self._ball.y > self._lv_data['ww'] or self._ball.y > SH + 60:
            self._die(); return

        # Flag
        if br.colliderect(self._flag.rect()):
            if not self._level_done:
                self._level_done = True
                self._done_timer = 80
                star_bonus = self._stars_got * 50
                self._score += star_bonus + 500
                if self._score > self._hi:
                    self._hi = self._score
                    self._save_hi()
                snd.play_win()

        if self._level_done:
            self._done_timer -= 1
            if self._done_timer <= 0:
                if self._lv + 1 < len(LEVELS):
                    self._lv += 1
                    self._load_level(self._lv)
                else:
                    self._state = 'victory'

        self._flag.update()
        self._cam.update(self._ball.x, self._lv_data['ww'])

        self._particles = [p for p in self._particles if p.life > 0]
        for p in self._particles: p.update()

        if self._flash > 0: self._flash -= 1

    def _die(self):
        if self._flash > 0: return
        self._flash = 20
        self._lives -= 1
        self._spawn_particles(self._ball.x, self._ball.y, BALLF, 16)
        snd.play_die()
        if self._lives <= 0:
            self._state = 'game_over'
        else:
            self._ball.reset(*self._lv_data['start'])
            self._cam.x = 0.0

    def _draw_play(self):
        cx = self._cam.x
        ld = self._lv_data

        # Background sky
        draw_sky(screen, ld['bg'])

        # Draw static platforms
        for p in self._plats:
            px = p.x - cx
            if px > SW or px + p.w < 0: continue
            pygame.draw.rect(screen, GND,  (px, p.y, p.w, p.h))
            pygame.draw.rect(screen, DIRT, (px, p.y + 12, p.w, p.h - 12))
            pygame.draw.rect(screen, (60,130,48),(px, p.y, p.w, 12))
            pygame.draw.rect(screen, (0,0,0), (px, p.y, p.w, p.h), 1)

        # Moving platforms
        for m in self._mplats: m.draw(screen, cx)

        # Spikes
        draw_spikes(screen, self._spikes, cx)

        # Stars
        for s in self._stars: s.draw(screen, cx)

        # Enemies
        for e in self._enemies: e.draw(screen, cx)

        # Flag
        self._flag.draw(screen, cx)

        # Particles
        for p in self._particles: p.draw(screen, cx)

        # Ball
        self._ball.draw(screen, cx)

        # Flash on death
        if self._flash > 0:
            a = min(180, self._flash * 14)
            fl = pygame.Surface((SW, SH), pygame.SRCALPHA)
            fl.fill((255, 60, 60, a))
            screen.blit(fl, (0, 0))

        # HUD
        self._draw_hud()

        # Level complete banner
        if self._level_done:
            ov = pygame.Surface((SW, 100), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, (0, SH//2 - 50))
            if self._lv + 1 < len(LEVELS):
                msg = f"Level {self._lv+1} Complete!"
                sub = f"Next: {LEVELS[self._lv+1]['name']}"
            else:
                msg = "All Levels Done!"
                sub = "You Win!"
            t1 = self.font_med.render(msg, True, YELLOW)
            t2 = self.font_sm.render(sub, True, WHITE)
            screen.blit(t1, t1.get_rect(center=(SW//2, SH//2 - 18)))
            screen.blit(t2, t2.get_rect(center=(SW//2, SH//2 + 18)))

    def _draw_hud(self):
        # Lives
        lbl = self.font_sm.render(f'❤ {self._lives}', True, RED)
        screen.blit(lbl, (12, 10))
        # Score
        sc  = self.font_sm.render(f'Score: {self._score}', True, WHITE)
        screen.blit(sc, (12, 32))
        # Stars
        st  = self.font_sm.render(f'★ {self._stars_got}/{self._stars_total}', True, STARY)
        screen.blit(st, (12, 54))
        # Level name
        nm  = self.font_sm.render(f'Lv {self._lv+1}: {self._lv_data["name"]}', True, CYAN)
        screen.blit(nm, nm.get_rect(midtop=(SW//2, 10)))
        # Hi
        hi  = self.font_xs.render(f'Best: {self._hi}', True, GRAY)
        screen.blit(hi, hi.get_rect(topright=(SW-10, 10)))

    # ── Menu ──────────────────────────────────────────────────────────────────
    def _draw_menu(self):
        # Animated starfield
        for i, (sx, sy, sp) in enumerate(self._menu_stars):
            self._menu_stars[i] = (sx, (sy + sp * 0.3) % (SH//2), sp)
            sz = int(sp)
            pygame.draw.circle(screen, WHITE, (int(sx), int(sy)), sz)

        screen.fill(DARK)
        for i, (sx, sy, sp) in enumerate(self._menu_stars):
            sz = max(1, int(sp * 0.7))
            pygame.draw.circle(screen, (200,200,220), (int(sx), int(sy)), sz)

        # Title
        t1 = self.font_big.render('RED BALL', True, RED)
        t2 = self.font_sm.render ('Rolling Adventure', True, STARY)
        screen.blit(t1, t1.get_rect(center=(SW//2, 170)))
        screen.blit(t2, t2.get_rect(center=(SW//2, 228)))

        # Bouncing ball demo
        bt = pygame.time.get_ticks() / 1000
        bx = SW//2
        by = int(310 + abs(math.sin(bt * 2.5)) * -40 + 40)
        ba = bt * 120
        bs = pygame.Surface((BR*2, BR*2), pygame.SRCALPHA)
        pygame.draw.circle(bs, BALLF, (BR,BR), BR)
        pygame.draw.circle(bs, BALLD, (BR,BR), BR, 3)
        ang = math.radians(ba)
        pygame.draw.line(bs, BALLD, (BR,BR),
                         (int(BR + math.cos(ang)*(BR-4)), int(BR + math.sin(ang)*(BR-4))), 3)
        pygame.draw.ellipse(bs, BALLH, (BR//2-2, BR//2-2, BR//2+2, BR//2+2))
        screen.blit(bs, (bx-BR, by-BR))
        # Shadow
        sha = int(60 * (1 - (by - 270) / 60)) if by > 270 else 60
        pygame.draw.ellipse(screen, (30,30,30), (bx-BR, 358, BR*2, 8))

        # Buttons
        buttons = [('PLAY', 'play'), ('CONTROLS', 'help')]
        self._btn_rects = {}
        for i, (label, key) in enumerate(buttons):
            bw, bh = 200, 48
            bx2 = SW//2 - bw//2
            by2 = 390 + i * 64
            r   = pygame.Rect(bx2, by2, bw, bh)
            self._btn_rects[key] = r
            hov = self._hover == key
            pygame.draw.rect(screen, (80,15,15) if hov else (50,8,8), r, border_radius=10)
            pygame.draw.rect(screen, RED if hov else (160,30,30), r, 2, border_radius=10)
            lt  = self.font_med.render(label, True, WHITE if hov else GRAY)
            screen.blit(lt, lt.get_rect(center=r.center))

        hi = self.font_sm.render(f'Best score: {self._hi}', True, GRAY)
        screen.blit(hi, hi.get_rect(center=(SW//2, SH - 30)))

        ctrl = self.font_xs.render('Move: ← → / A D    Jump: Space / ↑ / W', True, (80,80,90))
        screen.blit(ctrl, ctrl.get_rect(center=(SW//2, SH-12)))

    def _draw_help(self):
        screen.fill(DARK)
        ctr(screen, 'CONTROLS', 80, CYAN, 36)
        lines = [
            ('Move Left/Right', '← → or A D'),
            ('Jump',            'Space / ↑ / W'),
            ('Stomp enemies',   'Jump on their head'),
            ('Collect stars',   'Touch yellow stars'),
            ('Finish level',    'Reach the orange flag'),
        ]
        for i, (act, key) in enumerate(lines):
            y = 160 + i * 54
            pygame.draw.rect(screen, (20,25,40), (SW//2-280, y-8, 560, 44), border_radius=8)
            pygame.draw.rect(screen, (50,60,90), (SW//2-280, y-8, 560, 44), 1, border_radius=8)
            a = self.font_sm.render(act, True, WHITE)
            k = self.font_sm.render(key, True, CYAN)
            screen.blit(a, (SW//2-270, y+4))
            screen.blit(k, k.get_rect(midright=(SW//2+270, y+14)))

        self._btn_rects = {}
        r = pygame.Rect(SW//2-100, SH-80, 200, 44)
        self._btn_rects['back'] = r
        hov = self._hover == 'back'
        pygame.draw.rect(screen, (40,60,40) if hov else (25,40,25), r, border_radius=10)
        pygame.draw.rect(screen, GREEN if hov else (60,120,60), r, 2, border_radius=10)
        lt = self.font_med.render('BACK', True, WHITE)
        screen.blit(lt, lt.get_rect(center=r.center))

    def _draw_game_over(self):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        screen.blit(ov, (0, 0))
        ctr(screen, 'GAME OVER', SH//2 - 80, RED, 52)
        ctr(screen, f'Score: {self._score}', SH//2 - 20, WHITE, 28)
        if self._score >= self._hi:
            ctr(screen, 'NEW BEST!', SH//2 + 20, YELLOW, 24)
        self._btn_rects = {}
        for i, (lbl, key) in enumerate([('RETRY', 'retry'), ('MENU', 'menu')]):
            r = pygame.Rect(SW//2 - 110 + i*130, SH//2 + 70, 100, 42)
            self._btn_rects[key] = r
            hov = self._hover == key
            pygame.draw.rect(screen, (60,10,10) if hov else (35,5,5), r, border_radius=8)
            pygame.draw.rect(screen, RED if hov else (120,20,20), r, 2, border_radius=8)
            lt = self.font_sm.render(lbl, True, WHITE)
            screen.blit(lt, lt.get_rect(center=r.center))

    def _draw_victory(self):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        screen.blit(ov, (0, 0))
        ctr(screen, '★ YOU WIN! ★', SH//2 - 90, YELLOW, 48)
        ctr(screen, f'Final score: {self._score}', SH//2 - 30, WHITE, 28)
        ctr(screen, f'Stars: {self._stars_got}', SH//2 + 10, STARY, 22)
        if self._score >= self._hi:
            ctr(screen, f'New Best: {self._hi}!', SH//2 + 44, CYAN, 22)
        self._btn_rects = {}
        r = pygame.Rect(SW//2 - 100, SH//2 + 90, 200, 44)
        self._btn_rects['menu'] = r
        hov = self._hover == 'menu'
        pygame.draw.rect(screen, (10,60,10) if hov else (5,35,5), r, border_radius=10)
        pygame.draw.rect(screen, GREEN if hov else (20,100,20), r, 2, border_radius=10)
        lt = self.font_med.render('MENU', True, WHITE)
        screen.blit(lt, lt.get_rect(center=r.center))

    def _check_hover(self):
        mx, my = pygame.mouse.get_pos()
        if _ANDROID:
            mx = (mx - _rox) / max(1, _rscale)
            my = (my - _roy) / max(1, _rscale)
        self._hover = ''
        for k, r in self._btn_rects.items():
            if r.collidepoint(mx, my):
                self._hover = k
                break

    def _draw_touch_hints(self):
        h = pygame.Surface((SW, int(SH * 0.45)), pygame.SRCALPHA)
        bw = int(SW * 0.30)
        mw = int(SW * 0.35)
        rw = SW - bw - mw
        fnt = pygame.font.SysFont(None, 64)
        zones = [
            (0,   h.get_height(), bw, '←'),
            (bw,  h.get_height(), mw, '→'),
            (bw + mw, h.get_height(), rw, '↑'),
        ]
        for x, ht, w, lbl in zones:
            pygame.draw.rect(h, (255, 255, 255, 28), (x, 0, w, ht))
            pygame.draw.rect(h, (255, 255, 255, 55), (x, 0, w, ht), 2)
            lt = fnt.render(lbl, True, (255, 255, 255))
            lt.set_alpha(120)
            h.blit(lt, lt.get_rect(center=(x + w // 2, ht // 2)))
        screen.blit(h, (0, SH - h.get_height()))

    def _handle_click(self, pos):
        for k, r in getattr(self, '_btn_rects', {}).items():
            if r.collidepoint(pos):
                snd.play_click()
                self._btn_action(k)
                return

    def _btn_action(self, k):
        if k == 'play':
            self._lv    = 0
            self._lives = 3
            self._score = 0
            self._load_level(0)
            self._state = 'play'
        elif k == 'help':  self._state = 'help'
        elif k == 'back':  self._state = 'menu'
        elif k == 'retry':
            self._lives = 3
            self._score = 0
            self._load_level(self._lv)
            self._state = 'play'
        elif k == 'menu':
            self._state = 'menu'

    async def run(self):
        keys_state = {}
        while True:
            keys = pygame.key.get_pressed()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        if self._state == 'play': self._state = 'menu'
                        elif self._state in ('help','game_over','victory'): self._state = 'menu'
                        else: pygame.quit(); sys.exit()
                    if ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        if self._state == 'play':
                            self._ball.jump_press()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if _ANDROID:
                        mx, my = ev.pos
                        gx = (mx - _rox) / max(1, _rscale)
                        gy = (my - _roy) / max(1, _rscale)
                        self._handle_click((gx, gy))
                    else:
                        self._handle_click(ev.pos)
                if ev.type == pygame.FINGERDOWN:
                    gx, gy = _finger_to_game(ev.x, ev.y)
                    _touch_fingers[ev.finger_id] = (gx, gy)
                    if gy > SH * 0.55 and gx > SW * 0.65 and self._state == 'play':
                        self._ball.jump_press()
                    _update_touch_state()
                    if self._state != 'play':
                        self._handle_click((gx, gy))
                if ev.type == pygame.FINGERUP:
                    _touch_fingers.pop(ev.finger_id, None)
                    _update_touch_state()
                if ev.type == pygame.FINGERMOTION:
                    gx, gy = _finger_to_game(ev.x, ev.y)
                    _touch_fingers[ev.finger_id] = (gx, gy)
                    _update_touch_state()

            if self._state == 'play':
                self._update_play(keys)
                self._draw_play()
                if _ANDROID:
                    self._draw_touch_hints()
            elif self._state == 'menu':
                self._draw_menu()
                self._check_hover()
            elif self._state == 'help':
                self._draw_help()
                self._check_hover()
            elif self._state == 'game_over':
                self._draw_play()
                self._draw_game_over()
                self._check_hover()
            elif self._state == 'victory':
                self._draw_play()
                self._draw_victory()
                self._check_hover()

            if _ANDROID:
                scaled = pygame.transform.scale(screen, (_rsw, _rsh))
                _real_screen.fill((0, 0, 0))
                _real_screen.blit(scaled, (_rox, _roy))
            pygame.display.flip()
            clock.tick(FPS)
            await asyncio.sleep(0)


async def main():
    game = Game()
    await game.run()

if __name__ == '__main__':
    asyncio.run(main())
