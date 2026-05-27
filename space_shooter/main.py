import pygame
import random
import sys
import math
import json
import os

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ─── Constants ────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 900
SCREEN_HEIGHT = 600
FPS           = 60

# ─── Colours ──────────────────────────────────────────────────────────────────
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
RED        = (220, 50,  50)
DARK_RED   = (140, 0,   0)
YELLOW     = (255, 220, 0)
CYAN       = (0,   200, 255)
ORANGE     = (255, 140, 0)
GREEN      = (50,  200, 50)
GRAY       = (150, 150, 150)
DARK_GRAY  = (40,  40,  40)
BLUE       = (50,  100, 255)
PURPLE     = (160, 30,  220)
GOLD       = (200, 160, 0)
CRIMSON    = (139, 0,   0)
DARK_CRIMSON = (80, 0,  0)

# ─── Levels data ──────────────────────────────────────────────────────────────
# Each entry: (enemy_weights_dict, enemy_count, score_target, end_boss_list)
LEVELS_DATA = [
    # 1
    ({'fighter': 1},                       15, 500,   []),
    # 2
    ({'fighter': 1},                       20, 800,   []),
    # 3
    ({'fighter': 3, 'scout': 1},           25, 1200,  []),
    # 4
    ({'fighter': 2, 'scout': 1},           30, 1600,  []),
    # 5  — boss-only wave
    ({},                                    0, 0,     ['mini', 'mini', 'mini']),
    # 6
    ({'fighter': 4, 'scout': 2, 'heavy': 1}, 25, 2000, []),
    # 7
    ({'fighter': 3, 'scout': 2, 'heavy': 1}, 28, 2400, []),
    # 8
    ({'fighter': 3, 'scout': 2, 'heavy': 2}, 32, 2900, []),
    # 9
    ({'fighter': 3, 'scout': 2, 'heavy': 2}, 40, 3500, []),
    # 10
    ({'fighter': 3, 'scout': 2, 'heavy': 2}, 30, 4000, ['mini']),
    # 11
    ({'fighter': 3, 'scout': 2, 'heavy': 2}, 32, 4500, ['mini']),
    # 12
    ({'fighter': 2, 'scout': 2, 'heavy': 3}, 35, 5000, ['mini']),
    # 13
    ({'fighter': 2, 'scout': 2, 'heavy': 3}, 38, 5500, ['mini']),
    # 14
    ({'fighter': 2, 'scout': 2, 'heavy': 3}, 40, 6000, ['mini']),
    # 15
    ({'fighter': 2, 'scout': 2, 'heavy': 3}, 40, 7000, ['mini', 'mini']),
    # 16
    ({'fighter': 2, 'scout': 3, 'heavy': 3}, 42, 8000, ['mini', 'mini']),
    # 17
    ({'fighter': 2, 'scout': 3, 'heavy': 3}, 45, 9000, ['mini', 'mini']),
    # 18
    ({'fighter': 2, 'scout': 3, 'heavy': 4}, 50, 10000, ['mini', 'mini']),
    # 19
    ({'fighter': 2, 'scout': 3, 'heavy': 4}, 50, 12000, ['mini', 'mini', 'mini']),
    # 20
    ({'fighter': 2, 'scout': 3, 'heavy': 4}, 55, 14000, ['mini', 'mini', 'mini', 'FINAL']),
]


# ══════════════════════════════════════════════════════════════════════════════
#  SCREEN EFFECTS
# ══════════════════════════════════════════════════════════════════════════════
class ScreenEffects:
    def __init__(self):
        self.shake = 0.0
        self.shake_offset = (0, 0)
        self.flash_alpha = 0.0
        self.vignette_alpha = 0.0
        self._rnd_flash_interval = 0
        self._rnd_flash_timer = 0

    def add_shake(self, intensity: float):
        self.shake = max(self.shake, float(intensity))

    def add_flash(self, alpha: float):
        self.flash_alpha = min(255.0, self.flash_alpha + alpha)

    def set_vignette(self, alpha: float):
        self.vignette_alpha = float(alpha)

    def set_random_flashes(self, interval: int):
        self._rnd_flash_interval = interval
        self._rnd_flash_timer = interval

    def update(self):
        # Decay shake
        if self.shake > 0:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
            self.shake_offset = (int(ox), int(oy))
            self.shake *= 0.82
            if self.shake < 0.5:
                self.shake = 0.0
                self.shake_offset = (0, 0)
        else:
            self.shake_offset = (0, 0)

        # Decay flash
        if self.flash_alpha > 0:
            self.flash_alpha = max(0.0, self.flash_alpha - 15.0)

        # Random flashes
        if self._rnd_flash_interval > 0:
            self._rnd_flash_timer -= 1
            if self._rnd_flash_timer <= 0:
                self._rnd_flash_timer = self._rnd_flash_interval
                self.add_flash(random.uniform(30, 80))

    def draw_vignette(self, screen):
        if self.vignette_alpha <= 0:
            return
        alpha = int(min(255, self.vignette_alpha))
        thickness = 80
        for i in range(thickness):
            t = 1.0 - i / thickness
            a = int(alpha * t * t)
            if a <= 0:
                continue
            col = (180, 0, 0, a)
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(s, col, (i, i, SCREEN_WIDTH - i * 2, SCREEN_HEIGHT - i * 2), 2)
            screen.blit(s, (0, 0))

    def draw_flash(self, screen):
        if self.flash_alpha <= 0:
            return
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((255, 0, 0, int(self.flash_alpha)))
        screen.blit(s, (0, 0))

    def reset(self):
        self.shake = 0.0
        self.shake_offset = (0, 0)
        self.flash_alpha = 0.0
        self.vignette_alpha = 0.0
        self._rnd_flash_interval = 0
        self._rnd_flash_timer = 0


# ══════════════════════════════════════════════════════════════════════════════
#  SOUND MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class SoundManager:
    def __init__(self):
        self.enabled = False
        self._sounds: dict = {}
        self._init()

    def _init(self):
        if not _HAS_NUMPY:
            return
        try:
            pygame.mixer.pre_init(22050, -16, 2, 512)
            pygame.mixer.init()
            sr = 22050
            self._sounds = {
                'shoot':        self._sine(sr, 820,  0.07, decay=35, vol=0.22),
                'boom':         self._noise(sr, 0.30, decay=9,  vol=0.55),
                'hit':          self._sine(sr, 200,  0.18, decay=12, vol=0.45),
                'powerup':      self._rising(sr, 440, 880, 0.35, vol=0.40),
                'shield_break': self._sine(sr, 300,  0.25, decay=8,  vol=0.50),
                'boss_warning': self._sine(sr, 110,  0.60, decay=3,  vol=0.60),
                'boss_enrage':  self._enrage(sr),
                'boss_die':     self._noise(sr, 0.60, decay=4, vol=0.70),
                'level_complete': self._chord(sr, [261, 329, 392], vol=0.45),
                'victory':      self._fanfare(sr),
            }
            self._play_ambient(sr)
            self.enabled = True
        except Exception:
            pass

    @staticmethod
    def _to_sound(arr: 'np.ndarray') -> pygame.mixer.Sound:
        data = np.ascontiguousarray(np.column_stack([arr, arr]).astype(np.int16))
        return pygame.sndarray.make_sound(data)

    def _sine(self, sr, freq, dur, decay=8.0, vol=0.35):
        t = np.linspace(0, dur, int(sr * dur), False)
        return self._to_sound(np.sin(2*np.pi*freq*t) * np.exp(-decay*t) * vol * 32767)

    def _noise(self, sr, dur, decay=10.0, vol=0.4):
        n, t = int(sr*dur), np.linspace(0, dur, int(sr*dur), False)
        return self._to_sound(np.random.uniform(-1, 1, n) * np.exp(-decay*t) * vol * 32767)

    def _rising(self, sr, f0, f1, dur, vol=0.35):
        n = int(sr * dur)
        t = np.linspace(0, dur, n, False)
        freq = f0 + (f1-f0)*(t/dur)
        return self._to_sound(np.sin(2*np.pi*np.cumsum(freq)/sr) * np.exp(-2*t) * vol * 32767)

    def _enrage(self, sr=22050, vol=0.55):
        dur = 0.8
        t = np.linspace(0, dur, int(sr*dur), False)
        rumble = np.sin(2*np.pi*60*t) * 0.5
        freq = 300 + 500*(t/dur)
        rise = np.sin(2*np.pi*np.cumsum(freq)/sr) * 0.3
        return self._to_sound((rumble+rise) * np.exp(-t) * vol * 32767)

    def _chord(self, sr, freqs, vol=0.40):
        """Ascending 3-note chord played in sequence."""
        dur_each = 0.25
        total = dur_each * len(freqs)
        n = int(sr * total)
        out = np.zeros(n)
        for i, freq in enumerate(freqs):
            start = int(i * dur_each * sr)
            end = start + int(dur_each * 1.5 * sr)
            end = min(end, n)
            t = np.linspace(0, dur_each * 1.5, end - start, False)
            out[start:end] += np.sin(2*np.pi*freq*t) * np.exp(-3*t)
        out = np.clip(out * vol * 32767, -32767, 32767)
        return self._to_sound(out)

    def _fanfare(self, sr=22050, vol=0.45):
        """Triumphant 4-note fanfare."""
        notes = [261, 329, 392, 523]
        dur_each = 0.20
        total = dur_each * len(notes) + 0.4
        n = int(sr * total)
        out = np.zeros(n)
        for i, freq in enumerate(notes):
            start = int(i * dur_each * sr)
            end = start + int(0.6 * sr)
            end = min(end, n)
            t = np.linspace(0, 0.6, end - start, False)
            out[start:end] += np.sin(2*np.pi*freq*t) * np.exp(-2*t)
        out = np.clip(out * vol * 32767, -32767, 32767)
        return self._to_sound(out)

    def _play_ambient(self, sr=22050):
        dur = 5.0
        n, t = int(sr*dur), np.linspace(0, dur, int(sr*dur), False)
        wave = (np.sin(2*np.pi*55*t)*0.30 + np.sin(2*np.pi*82*t)*0.20
              + np.sin(2*np.pi*110*t)*0.12 + np.sin(2*np.pi*165*t)*0.08)
        wave *= 0.7 + 0.3*np.sin(2*np.pi*0.4*t)
        fl = int(sr*0.5)
        fade = np.ones(n)
        fade[:fl] = np.linspace(0, 1, fl)
        fade[-fl:] = np.linspace(1, 0, fl)
        wave = (wave*fade*32767*0.45).astype(np.int16)
        snd = pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([wave, wave])))
        snd.set_volume(0.35)
        snd.play(-1)

    def play(self, name: str):
        if self.enabled and name in self._sounds:
            self._sounds[name].play()


# ══════════════════════════════════════════════════════════════════════════════
#  STARS
# ══════════════════════════════════════════════════════════════════════════════
class Star:
    def __init__(self):   self._reset(anywhere=True)
    def _reset(self, anywhere=False):
        self.x      = random.randint(0, SCREEN_WIDTH) if anywhere else SCREEN_WIDTH+4
        self.y      = random.randint(0, SCREEN_HEIGHT)
        self.speed  = random.uniform(0.8, 4.0)
        self.radius = 1 if self.speed<2 else (2 if self.speed<3.2 else 3)
        self.bright = random.randint(120, 255)
    def update(self):
        self.x -= self.speed
        if self.x < 0: self._reset()
    def draw(self, surf):
        pygame.draw.circle(surf, (self.bright,)*3, (int(self.x), int(self.y)), self.radius)


# ══════════════════════════════════════════════════════════════════════════════
#  BULLETS
# ══════════════════════════════════════════════════════════════════════════════
class Bullet:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.speed = 14; self.W, self.H = 18, 5; self.active = True
    def update(self):
        self.x += self.speed
        if self.x > SCREEN_WIDTH+20: self.active = False
    def draw(self, surf):
        ix, iy = int(self.x), int(self.y)
        pygame.draw.rect(surf, YELLOW, (ix, iy-2, self.W, self.H))
        pygame.draw.rect(surf, WHITE,  (ix+4, iy-1, self.W-8, 3))
    def get_rect(self): return pygame.Rect(self.x, self.y-2, self.W, self.H)


class EnemyBullet:
    def __init__(self, x, y, angle_deg=180):
        self.x, self.y = float(x), float(y)
        rad = math.radians(angle_deg); spd = 6
        self.vx, self.vy = math.cos(rad)*spd, math.sin(rad)*spd
        self.active = True; self.R = 5
    def update(self):
        self.x += self.vx; self.y += self.vy
        if self.x<-20 or self.y<-20 or self.y>SCREEN_HEIGHT+20: self.active = False
    def draw(self, surf):
        pygame.draw.circle(surf, RED,    (int(self.x), int(self.y)), self.R)
        pygame.draw.circle(surf, ORANGE, (int(self.x), int(self.y)), self.R-2)
    def get_rect(self): return pygame.Rect(self.x-self.R, self.y-self.R, self.R*2, self.R*2)


# ══════════════════════════════════════════════════════════════════════════════
#  POWER-UPS
# ══════════════════════════════════════════════════════════════════════════════
class PowerUp:
    CONFIGS = {
        'double': dict(color=YELLOW,         label='2×',  duration=600, desc='Double Shot'),
        'shield': dict(color=CYAN,           label='SHD', duration=0,   desc='Shield'),
        'slow':   dict(color=PURPLE,         label='SLW', duration=300, desc='Slow Time'),
        'life':   dict(color=(220, 80, 100), label='+HP', duration=0,   desc='Extra Life'),
    }
    def __init__(self, x, y, kind=None):
        self.kind    = kind or random.choice(list(self.CONFIGS.keys()))
        cfg          = self.CONFIGS[self.kind]
        self.color   = cfg['color']; self.label = cfg['label']
        self.duration= cfg['duration']; self.desc = cfg['desc']
        self.x, self.y = float(x), float(y)
        self.vx = -2.0; self.vy = random.uniform(-0.8, 0.8)
        self.angle = 0.0; self.active = True; self.R = 15
    def update(self):
        self.x += self.vx; self.y += self.vy; self.angle += 4
        if self.y<self.R or self.y>SCREEN_HEIGHT-self.R: self.vy *= -1
        if self.x < -40: self.active = False
    def draw(self, surf, font_s):
        if not self.active: return
        x, y = int(self.x), int(self.y)
        pulse = int(4*math.sin(math.radians(self.angle*3)))
        for r, alpha in [(self.R+pulse+7,50),(self.R+pulse+3,90)]:
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (r,r), r)
            surf.blit(s, (x-r, y-r))
        angle_rad = math.radians(self.angle)
        for i in range(6):
            a = angle_rad + i*math.pi/3
            pygame.draw.circle(surf, WHITE, (x+int((self.R+1)*math.cos(a)), y+int((self.R+1)*math.sin(a))), 2)
        pygame.draw.circle(surf, self.color, (x, y), self.R)
        pygame.draw.circle(surf, WHITE,      (x, y), self.R, 2)
        t = font_s.render(self.label, True, BLACK)
        surf.blit(t, t.get_rect(center=(x, y)))
    def get_rect(self): return pygame.Rect(self.x-self.R, self.y-self.R, self.R*2, self.R*2)


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYER
# ══════════════════════════════════════════════════════════════════════════════
class Player:
    MAX_HP = 5
    def __init__(self):
        self.x, self.y  = 120.0, float(SCREEN_HEIGHT//2)
        self.speed       = 5
        self.health      = 3
        self.shoot_cd    = 0; self.shoot_delay = 14
        self.inv_frames  = 0; self.just_shot   = False
        self.bullets: list[Bullet] = []
        self.double_timer= 0; self.slow_timer = 0; self.has_shield = False

    def update(self, keys):
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.y -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.y += self.speed
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.x += self.speed
        self.x = max(30, min(SCREEN_WIDTH//2, self.x))
        self.y = max(30, min(SCREEN_HEIGHT-30, self.y))
        if self.shoot_cd > 0: self.shoot_cd -= 1
        self.just_shot = False
        if keys[pygame.K_SPACE] and self.shoot_cd == 0: self._shoot()
        if self.inv_frames   > 0: self.inv_frames   -= 1
        if self.double_timer > 0: self.double_timer -= 1
        if self.slow_timer   > 0: self.slow_timer   -= 1
        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def _shoot(self):
        bx = self.x + 32
        if self.double_timer > 0:
            self.bullets.append(Bullet(bx, self.y-9))
            self.bullets.append(Bullet(bx, self.y+9))
        else:
            self.bullets.append(Bullet(bx, self.y))
        self.shoot_cd = self.shoot_delay; self.just_shot = True

    def take_damage(self) -> bool:
        if self.has_shield:
            self.has_shield = False; self.inv_frames = 30; return False
        if self.inv_frames == 0:
            self.health -= 1; self.inv_frames = 90; return True
        return False

    def apply_powerup(self, kind: str):
        if   kind == 'double': self.double_timer = 600
        elif kind == 'shield': self.has_shield   = True
        elif kind == 'slow':   self.slow_timer   = 300
        elif kind == 'life':   self.health = min(self.health+1, self.MAX_HP)

    @property
    def slow_active(self): return self.slow_timer > 0

    def draw(self, surf):
        if self.inv_frames > 0 and (self.inv_frames//5)%2 == 0: return
        x, y = int(self.x), int(self.y)
        if self.has_shield:
            r = 38
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0,200,255,55), (r,r), r)
            surf.blit(s, (x-r, y-r))
            pygame.draw.circle(surf, CYAN, (x,y), r, 2)
        pygame.draw.polygon(surf, BLUE,      [(x-22,y-10),(x-5,y-26),(x+12,y-6)])
        pygame.draw.polygon(surf, BLUE,      [(x-22,y+10),(x-5,y+26),(x+12,y+6)])
        body_col = YELLOW if self.double_timer > 0 else CYAN
        pygame.draw.polygon(surf, body_col,      [(x-28,y+12),(x+32,y),(x-28,y-12)])
        pygame.draw.polygon(surf, (0,160,210),   [(x-28,y+12),(x+32,y),(x-28,y-12)], 1)
        fl = random.randint(12,22)
        pygame.draw.polygon(surf, ORANGE, [(x-28,y-5),(x-28-fl,y),(x-28,y+5)])
        pygame.draw.polygon(surf, YELLOW, [(x-28,y-2),(x-28-fl//2,y),(x-28,y+2)])
        pygame.draw.circle(surf, WHITE, (x+12,y), 6); pygame.draw.circle(surf, CYAN,(x+12,y),4)
        if self.double_timer > 0:
            pygame.draw.line(surf, YELLOW, (x,y-26),(x+36,y-26),1)
            pygame.draw.line(surf, YELLOW, (x,y+26),(x+36,y+26),1)
        for b in self.bullets: b.draw(surf)

    def get_rect(self): return pygame.Rect(self.x-26, self.y-13, 52, 26)


# ══════════════════════════════════════════════════════════════════════════════
#  REGULAR ENEMIES
# ══════════════════════════════════════════════════════════════════════════════
class Enemy:
    TYPES = {
        'fighter': dict(speed=(3.0,5.5), hp=1, w=42, h=26, score=100,  shoot_cd=(70,140), drop=0.20),
        'scout':   dict(speed=(5.5,8.5), hp=1, w=30, h=20, score=150,  shoot_cd=(90,180), drop=0.20),
        'heavy':   dict(speed=(1.5,2.8), hp=3, w=56, h=38, score=300,  shoot_cd=(50,100), drop=0.45),
    }
    def __init__(self, kind: str):
        cfg = self.TYPES[kind]
        self.kind=kind; self.hp=cfg['hp']; self.max_hp=cfg['hp']
        self.W,self.H=cfg['w'],cfg['h']; self.score_val=cfg['score']
        self.drop_chance=cfg['drop']
        self.x=float(SCREEN_WIDTH+self.W); self.y=float(random.randint(50,SCREEN_HEIGHT-50))
        self.speed=random.uniform(*cfg['speed']); self.vy=random.uniform(-1.2,1.2)
        lo,hi=cfg['shoot_cd']; self.shoot_timer=random.randint(lo,hi); self.shoot_range=(lo,hi)
        self.bullets: list[EnemyBullet]=[]; self.active=True

    def update(self, time_scale=1.0):
        self.x-=self.speed*time_scale; self.y+=self.vy*time_scale
        if self.y<40 or self.y>SCREEN_HEIGHT-40: self.vy*=-1
        if self.x<-self.W-20: self.active=False
        self.shoot_timer-=time_scale
        if self.shoot_timer<=0:
            lo,hi=self.shoot_range; self.shoot_timer=random.randint(lo,hi)
            bx=self.x-self.W//2
            if self.kind=='heavy':
                for ang in [175,180,185]: self.bullets.append(EnemyBullet(bx,self.y,ang))
            else: self.bullets.append(EnemyBullet(bx,self.y))
        for b in self.bullets: b.update()
        self.bullets=[b for b in self.bullets if b.active]

    def take_hit(self)->bool: self.hp-=1; return self.hp<=0
    def should_drop(self)->bool: return random.random()<self.drop_chance

    def draw(self, surf):
        x,y=int(self.x),int(self.y)
        if self.kind=='fighter':
            pygame.draw.polygon(surf,RED,    [(x+20,y),(x-20,y-13),(x-20,y+13)])
            pygame.draw.polygon(surf,DARK_RED,[(x-10,y-13),(x+2,y-26),(x+12,y-5)])
            pygame.draw.polygon(surf,DARK_RED,[(x-10,y+13),(x+2,y+26),(x+12,y+5)])
            pygame.draw.circle(surf,ORANGE,(x+18,y),4); pygame.draw.circle(surf,YELLOW,(x+18,y),2)
        elif self.kind=='scout':
            pygame.draw.polygon(surf,PURPLE,[(x+14,y),(x-14,y-10),(x-14,y+10)])
            pygame.draw.circle(surf,WHITE,(x+4,y),4); pygame.draw.circle(surf,PURPLE,(x+4,y),2)
        else:
            pygame.draw.ellipse(surf,ORANGE,    (x-27,y-18,56,38))
            pygame.draw.ellipse(surf,(200,90,0),(x-13,y-10,28,22))
            pygame.draw.rect(surf,GRAY,(x+15,y-22,18,6)); pygame.draw.rect(surf,GRAY,(x+15,y+16,18,6))
            pygame.draw.circle(surf,YELLOW,(x+26,y),7); pygame.draw.circle(surf,ORANGE,(x+26,y),4)
            bw=44; filled=max(0,int(bw*self.hp/self.max_hp))
            pygame.draw.rect(surf,DARK_GRAY,(x-22,y-30,bw,6))
            pygame.draw.rect(surf,GREEN,    (x-22,y-30,filled,6))
        for b in self.bullets: b.draw(surf)

    def get_rect(self): return pygame.Rect(self.x-self.W//2,self.y-self.H//2,self.W,self.H)


# ══════════════════════════════════════════════════════════════════════════════
#  MINI-BOSS — Marauder
# ══════════════════════════════════════════════════════════════════════════════
class MiniBoss:
    def __init__(self):
        self.x = float(SCREEN_WIDTH + 80)
        self.y = float(SCREEN_HEIGHT // 2)
        self.hp = 8; self.max_hp = 8
        self.W, self.H = 72, 48
        self.score_val = 1500; self.kill_credit = 3; self.drop_count = 2
        self.active = True
        self.bullets: list[EnemyBullet] = []
        self.shoot_timer = 90
        self.move_timer  = 0.0
        self._target_x   = SCREEN_WIDTH * 0.68
        self.entering    = True

    def update(self, time_scale=1.0, effects=None):
        if self.x > self._target_x:
            self.x -= 3.5 * time_scale
        else:
            self.entering = False
            self.move_timer += time_scale
            self.y = SCREEN_HEIGHT//2 + math.sin(self.move_timer * 0.025) * 165
            self.y = max(55, min(SCREEN_HEIGHT-55, self.y))

        if not self.entering:
            self.shoot_timer -= time_scale
            if self.shoot_timer <= 0:
                self.shoot_timer = 52
                for ang in range(162, 203, 8):
                    self.bullets.append(EnemyBullet(self.x-self.W//2, self.y, ang))

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def take_hit(self) -> bool: self.hp -= 1; return self.hp <= 0

    def get_laser_rects(self):
        return []

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.polygon(surf, (150,120,0), [(x-36,y-10),(x-8,y-38),(x+22,y-10)])
        pygame.draw.polygon(surf, (150,120,0), [(x-36,y+10),(x-8,y+38),(x+22,y+10)])
        pygame.draw.ellipse(surf, GOLD,   (x-36,y-23,72,46))
        pygame.draw.ellipse(surf, YELLOW, (x-18,y-13,36,26))
        for dy in (-16,-6,4,14):
            pygame.draw.rect  (surf, GRAY,   (x-46,y+dy-3,18,6))
            pygame.draw.circle(surf, ORANGE, (x-46,y+dy), 3)
        pygame.draw.circle(surf, YELLOW, (x,y), 13)
        pygame.draw.circle(surf, WHITE,  (x,y), 7)
        for i in range(4):
            a = math.radians(self.move_timer*3 + i*90)
            pygame.draw.circle(surf, (255,200,0), (x+int(10*math.cos(a)), y+int(10*math.sin(a))), 3)
        bw = 80; filled = max(0, int(bw*self.hp/self.max_hp))
        pygame.draw.rect(surf, DARK_GRAY, (x-40,y-42,bw,8))
        pygame.draw.rect(surf, YELLOW,    (x-40,y-42,filled,8))
        pygame.draw.rect(surf, GRAY,      (x-40,y-42,bw,8), 1)
        for b in self.bullets: b.draw(surf)

    def get_rect(self): return pygame.Rect(self.x-self.W//2, self.y-self.H//2, self.W, self.H)


# ══════════════════════════════════════════════════════════════════════════════
#  BIG BOSS — Dreadnought (arcade mode only)
# ══════════════════════════════════════════════════════════════════════════════
class Boss:
    LASER_DURATION = 105
    LASER_CD       = 230

    def __init__(self):
        self.x = float(SCREEN_WIDTH + 130)
        self.y = float(SCREEN_HEIGHT // 2)
        self.hp = 25; self.max_hp = 25
        self.W, self.H = 114, 78
        self.score_val = 5000; self.kill_credit = 6; self.drop_count = 4
        self.active  = True
        self.phase   = 1
        self.bullets: list[EnemyBullet] = []
        self.shoot_timer = 100
        self.move_timer  = 0.0
        self._target_x   = SCREEN_WIDTH * 0.72
        self.entering    = True
        self.laser_active= False
        self.laser_timer = 0.0
        self.laser_cd    = 0.0

    def update(self, time_scale=1.0, effects=None):
        if self.x > self._target_x:
            self.x -= 2.5 * time_scale
        else:
            self.entering = False
            self.move_timer += time_scale
            amp = 195 if self.phase == 2 else 155
            spd = 0.020 if self.phase == 2 else 0.014
            self.y = SCREEN_HEIGHT//2 + math.sin(self.move_timer*spd)*amp
            self.y = max(60, min(SCREEN_HEIGHT-60, self.y))

        if not self.entering:
            delay = 38 if self.phase == 2 else 58
            self.shoot_timer -= time_scale
            if self.shoot_timer <= 0:
                self.shoot_timer = delay
                angs = range(151,213,8) if self.phase==2 else range(155,210,11)
                for ang in angs:
                    self.bullets.append(EnemyBullet(self.x-self.W//2, self.y, ang))

            if self.phase == 2:
                if self.laser_active:
                    self.laser_timer -= time_scale
                    if self.laser_timer <= 0:
                        self.laser_active = False; self.laser_cd = self.LASER_CD
                elif self.laser_cd > 0:
                    self.laser_cd -= time_scale
                else:
                    self.laser_active = True; self.laser_timer = self.LASER_DURATION

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def take_hit(self) -> bool: self.hp -= 1; return self.hp <= 0

    def get_laser_rect(self):
        if not self.laser_active or self.laser_timer <= 0:
            return None
        x, y = int(self.x), int(self.y)
        return pygame.Rect(0, y-6, x-self.W//2, 12)

    def get_laser_rects(self):
        r = self.get_laser_rect()
        return [r] if r else []

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        lr = self.get_laser_rect()
        if lr:
            flickering = self.laser_timer > self.LASER_DURATION-20 or self.laser_timer < 20
            if not flickering or (int(self.laser_timer)//3)%2:
                pygame.draw.rect(surf, (255,40,40),  lr)
                pygame.draw.rect(surf, (255,160,160), pygame.Rect(lr.x,lr.y+4,lr.w,4))
                pygame.draw.rect(surf, WHITE,         pygame.Rect(lr.x,lr.y+5,lr.w,2))

        col_wing = (90,10,10) if self.phase==2 else (70,10,10)
        pygame.draw.polygon(surf, col_wing, [(x-52,y-28),(x-14,y-68),(x+32,y-22)])
        pygame.draw.polygon(surf, col_wing, [(x-52,y+28),(x-14,y+68),(x+32,y+22)])

        hull_col = (100,15,15) if self.phase==2 else (72,12,12)
        pygame.draw.ellipse(surf, hull_col,    (x-57,y-38,114,78))
        pygame.draw.ellipse(surf, (155,28,28), (x-28,y-19,58,40))

        for dy in (-30,-15,0,15,30):
            pygame.draw.rect  (surf, GRAY,   (x-66,y+dy-4,24,8))
            pygame.draw.circle(surf, ORANGE, (x-64,y+dy), 4)

        core_col  = (255,40,40)   if self.phase==2 else ORANGE
        inner_col = (255,200,0)   if self.phase==2 else YELLOW
        pygame.draw.circle(surf, core_col,  (x,y), 22)
        pygame.draw.circle(surf, inner_col, (x,y), 12)
        pygame.draw.circle(surf, WHITE,     (x,y), 5)

        if self.phase == 2:
            for i in range(8):
                a = math.radians(self.move_timer*4 + i*45)
                rx,ry = x+int(22*math.cos(a)), y+int(22*math.sin(a))
                pygame.draw.circle(surf,(255,80,80),(rx,ry),3)

        bw = 110; filled = max(0, int(bw*self.hp/self.max_hp))
        bar_col = RED if self.phase==2 else ORANGE
        pygame.draw.rect(surf, DARK_GRAY, (x-55,y-58,bw,10))
        pygame.draw.rect(surf, bar_col,   (x-55,y-58,filled,10))
        pygame.draw.rect(surf, GRAY,      (x-55,y-58,bw,10), 1)

        for b in self.bullets: b.draw(surf)

    def get_rect(self): return pygame.Rect(self.x-self.W//2, self.y-self.H//2, self.W, self.H)


# ══════════════════════════════════════════════════════════════════════════════
#  FINAL BOSS — Crimson Overlord (levels mode level 20)
# ══════════════════════════════════════════════════════════════════════════════
class FinalBoss:
    LASER_DURATION = 120
    LASER_CD       = 200

    def __init__(self):
        self.x = float(SCREEN_WIDTH + 150)
        self.y = float(SCREEN_HEIGHT // 2)
        self.hp = 50; self.max_hp = 50
        self.W, self.H = 150, 100
        self.score_val = 15000; self.kill_credit = 0; self.drop_count = 6
        self.active = True
        self.bullets: list[EnemyBullet] = []
        self.shoot_timer = 100
        self.move_timer  = 0.0
        self._target_x   = SCREEN_WIDTH * 0.73
        self.entering    = True
        # Laser state: list of [active, timer, cd, y_offset]
        self._lasers = [
            [False, 0.0, 0.0, -20],
            [False, 0.0, 0.0,  20],
            [False, 0.0, 0.0,   0],
        ]

    def _hp_ratio(self):
        return self.hp / self.max_hp

    @property
    def phase(self):
        r = self._hp_ratio()
        if r > 0.66:
            return 1
        elif r > 0.33:
            return 2
        else:
            return 3

    def _update_phase(self):
        pass  # phase is now a computed property

    def update(self, time_scale=1.0, effects=None):
        if self.x > self._target_x:
            self.x -= 2.0 * time_scale
        else:
            self.entering = False
            self.move_timer += time_scale
            amp = 160
            spd = 0.016 + (self.phase - 1) * 0.006
            self.y = SCREEN_HEIGHT//2 + math.sin(self.move_timer*spd)*amp
            self.y = max(70, min(SCREEN_HEIGHT-70, self.y))

        if not self.entering:
            # Shooting config per phase
            if self.phase == 1:
                shoot_delay = 51   # ~0.85s at 60fps
                n_spread = 7
                spread_range = (155, 206)
            elif self.phase == 2:
                shoot_delay = 40
                n_spread = 9
                spread_range = (152, 209)
            else:
                shoot_delay = 30
                n_spread = 12
                spread_range = (149, 212)

            self.shoot_timer -= time_scale
            if self.shoot_timer <= 0:
                self.shoot_timer = shoot_delay
                step = (spread_range[1] - spread_range[0]) // max(1, n_spread - 1)
                for i in range(n_spread):
                    ang = spread_range[0] + i * step
                    self.bullets.append(EnemyBullet(self.x - self.W//2, self.y, ang))
                # Phase 3: diagonal shots
                if self.phase == 3:
                    for ang in [135, 225, 145, 215]:
                        self.bullets.append(EnemyBullet(self.x - self.W//2, self.y, ang))
                # Shake on shot
                if effects:
                    shake_amount = {1: 5, 2: 10, 3: 16}[self.phase]
                    effects.add_shake(shake_amount)

            # Laser beams
            active_lasers = 0 if self.phase == 1 else (2 if self.phase == 2 else 3)
            for i, laser in enumerate(self._lasers):
                if i >= active_lasers:
                    laser[0] = False
                    continue
                if laser[0]:  # active
                    laser[1] -= time_scale
                    if laser[1] <= 0:
                        laser[0] = False
                        laser[2] = self.LASER_CD + i * 30
                elif laser[2] > 0:
                    laser[2] -= time_scale
                else:
                    laser[0] = True
                    laser[1] = self.LASER_DURATION

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def take_hit(self) -> bool:
        self.hp -= 1
        self._update_phase()
        return self.hp <= 0

    def get_laser_rects(self) -> list:
        rects = []
        for laser in self._lasers:
            active, timer, _, y_off = laser
            if active and timer > 0:
                lx = int(self.x) - self.W//2
                ly = int(self.y + y_off) - 6
                rects.append(pygame.Rect(0, ly, lx, 12))
        return rects

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        mt = self.move_timer

        # Draw laser beams
        for laser in self._lasers:
            if laser[0] and laser[1] > 0:
                lx = x - self.W//2
                ly = int(self.y + laser[3])
                flickering = laser[1] > self.LASER_DURATION - 20 or laser[1] < 20
                if not flickering or (int(laser[1])//3)%2:
                    pygame.draw.rect(surf, (200, 0, 0),   (0, ly-6, lx, 12))
                    pygame.draw.rect(surf, (255, 60, 60), (0, ly-3, lx, 6))
                    pygame.draw.rect(surf, WHITE,          (0, ly-1, lx, 2))

        # Giant wings
        wing_col = DARK_CRIMSON
        pygame.draw.polygon(surf, wing_col, [
            (x-70, y-20), (x-20, y-80), (x+30, y-30)
        ])
        pygame.draw.polygon(surf, wing_col, [
            (x-70, y+20), (x-20, y+80), (x+30, y+30)
        ])
        # Wing highlights
        pygame.draw.polygon(surf, CRIMSON, [
            (x-60, y-18), (x-18, y-70), (x+24, y-28)
        ])
        pygame.draw.polygon(surf, CRIMSON, [
            (x-60, y+18), (x-18, y+70), (x+24, y+28)
        ])

        # Main body
        pygame.draw.ellipse(surf, DARK_CRIMSON, (x-70, y-48, 140, 96))
        pygame.draw.ellipse(surf, CRIMSON,      (x-40, y-28, 82, 58))

        # 6 gun ports
        for i, dy in enumerate([-36, -20, -6, 6, 20, 36]):
            pygame.draw.rect  (surf, GRAY,        (x-82, y+dy-4, 20, 8))
            pygame.draw.circle(surf, (180, 20, 20), (x-80, y+dy), 5)
            pygame.draw.circle(surf, ORANGE,       (x-80, y+dy), 3)

        # Pulsing core
        pulse = abs(math.sin(mt * 0.08)) * 8
        core_r = int(26 + pulse)
        pygame.draw.circle(surf, (180, 0, 0),  (x, y), core_r)
        pygame.draw.circle(surf, (255, 40, 40), (x, y), core_r - 8)
        pygame.draw.circle(surf, (255, 160, 0), (x, y), core_r - 16)
        pygame.draw.circle(surf, WHITE,          (x, y), 6)

        # Orbiting dots (phase 2+)
        if self.phase >= 2:
            for i in range(6):
                a = math.radians(mt * 4 + i * 60)
                pygame.draw.circle(surf, (255, 60, 60),
                    (x + int(32*math.cos(a)), y + int(32*math.sin(a))), 4)

        # Double ring (phase 3)
        if self.phase == 3:
            for i in range(8):
                a = math.radians(mt * 6 + i * 45)
                pygame.draw.circle(surf, (255, 120, 0),
                    (x + int(50*math.cos(a)), y + int(50*math.sin(a))), 3)

        # HP bar
        bw = 130; filled = max(0, int(bw * self.hp / self.max_hp))
        bar_col = (255, 20, 20) if self.phase == 3 else ((200, 40, 40) if self.phase == 2 else CRIMSON)
        pygame.draw.rect(surf, DARK_GRAY, (x-65, y-70, bw, 10))
        pygame.draw.rect(surf, bar_col,   (x-65, y-70, filled, 10))
        pygame.draw.rect(surf, GRAY,      (x-65, y-70, bw, 10), 1)

        for b in self.bullets: b.draw(surf)

    def get_rect(self): return pygame.Rect(self.x-self.W//2, self.y-self.H//2, self.W, self.H)


# ══════════════════════════════════════════════════════════════════════════════
#  EXPLOSION
# ══════════════════════════════════════════════════════════════════════════════
class Explosion:
    def __init__(self, x, y, big=False):
        self.x, self.y = x, y; self.max_r=45 if big else 25
        self.frame=0; self.total=22; self.active=True
        self.sparks=[(random.uniform(0,math.tau),random.uniform(1.5,4.5))
                     for _ in range(12 if big else 6)]
    def update(self):
        self.frame+=1
        if self.frame>=self.total: self.active=False
    def draw(self, surf):
        t=self.frame/self.total; r=int(self.max_r*math.sin(t*math.pi))
        if r<=0: return
        pygame.draw.circle(surf,(255,int(180*(1-t)),0),(int(self.x),int(self.y)),r)
        if r>5: pygame.draw.circle(surf,(255,255,int(200*(1-t))),(int(self.x),int(self.y)),r//2)
        for ang,spd in self.sparks:
            pygame.draw.circle(surf,YELLOW,(int(self.x+math.cos(ang)*spd*self.frame),
                                             int(self.y+math.sin(ang)*spd*self.frame)),2)


# ══════════════════════════════════════════════════════════════════════════════
#  GAME
# ══════════════════════════════════════════════════════════════════════════════
class Game:
    ARCADE_WEIGHTS = {
        1: {'fighter':8,'scout':2,'heavy':0},
        2: {'fighter':6,'scout':3,'heavy':1},
        3: {'fighter':5,'scout':3,'heavy':2},
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Space Shooter")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.game_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock  = pygame.time.Clock()
        self.font   = pygame.font.Font(None, 36)
        self.font_b = pygame.font.Font(None, 74)
        self.font_s = pygame.font.Font(None, 24)
        self.font_xl = pygame.font.Font(None, 96)
        self.sounds = SoundManager()
        self.effects = ScreenEffects()
        self.mode = 'arcade'   # 'arcade' or 'levels'
        self.state = 'menu'
        self._menu_sel  = 0    # 0=ARCADE 1=LEVELS
        self._ls_cursor = 0    # level-select grid cursor (0-19)
        self._pause_sel = 0    # 0=Resume  1=Main Menu
        self._pause_surf: pygame.Surface | None = None
        self._save_path = os.path.join(os.path.dirname(__file__), 'save.json')
        self._max_unlocked = self._load_save()
        self._reset()

    def _reset(self):
        self.player      = Player()
        self.enemies:    list[Enemy]     = []
        self.powerups:   list[PowerUp]   = []
        self.explosions: list[Explosion] = []
        self.stars       = [Star() for _ in range(180)]
        self.score       = 0
        self.level       = 1
        self.kills       = 0
        self.kills_level = 10
        self.spawn_timer = 0
        self.spawn_delay = 90
        self.active_bosses: list = []
        self.bosses_spawned: set = set()
        self.boss_enraged    = False
        self.warning_text    = ""
        self.warning_timer   = 0
        self.enrage_flash    = 0
        self.effects.reset()

        # Levels-mode state
        self.lv_idx             = 0
        self.lv_wave_phase      = 'intro'
        self.lv_spawn_left      = 0
        self.lv_boss_queue: list = []
        self.lv_next_boss_timer = 0
        self.lv_final_delay_timer = 0
        self.lv_intro_timer     = 0
        self.lv_complete_timer  = 0
        self.lv_spawn_timer     = 0
        self.lv_spawn_delay     = 70

        if self.mode == 'levels':
            self._start_level()
        if self.state != 'menu':
            self.state = 'playing'

    def _start_level(self):
        weights, count, score_tgt, bosses = LEVELS_DATA[self.lv_idx]
        self.lv_spawn_left = count
        self.lv_boss_queue = list(bosses)
        self.lv_wave_phase = 'intro'
        self.lv_intro_timer = 140
        self.lv_spawn_timer = 0
        self.lv_spawn_delay = max(30, 90 - self.lv_idx * 3)
        self.enemies.clear()
        self.active_bosses.clear()
        self.level = self.lv_idx + 1

    def _spawn_enemy_arcade(self):
        lv = min(self.level, 3)
        w  = self.ARCADE_WEIGHTS[lv]
        self.enemies.append(Enemy(random.choices(list(w.keys()), list(w.values()))[0]))

    def _spawn_enemy_levels(self):
        weights, _, _, _ = LEVELS_DATA[self.lv_idx]
        if not weights:
            return
        kinds = list(weights.keys())
        wts   = list(weights.values())
        self.enemies.append(Enemy(random.choices(kinds, wts)[0]))

    def _check_boss_spawn_arcade(self):
        if self.active_bosses:
            return
        lv = self.level
        if lv in self.bosses_spawned:
            return
        if lv % 5 == 0:
            self.bosses_spawned.add(lv)
            self.enemies.clear()
            boss = Boss()
            self.active_bosses.append(boss)
            self.boss_enraged  = False
            self.warning_text  = "DREADNOUGHT"
            self.warning_timer = 190
            self.sounds.play('boss_warning')
        elif lv % 3 == 0:
            self.bosses_spawned.add(lv)
            mb = MiniBoss()
            self.active_bosses.append(mb)
            self.warning_text  = "MARAUDER"
            self.warning_timer = 130
            self.sounds.play('boss_warning')

    def _get_boss_laser_rects(self, boss) -> list:
        if isinstance(boss, FinalBoss):
            return boss.get_laser_rects()
        if isinstance(boss, Boss):
            return boss.get_laser_rects()
        return []  # MiniBoss has no laser

    def _boss_death(self, boss):
        """Handle any boss death."""
        count = 5 if isinstance(boss, (Boss, FinalBoss)) else 3
        for _ in range(count):
            ox = boss.x + random.randint(-55, 55)
            oy = boss.y + random.randint(-40, 40)
            self.explosions.append(Explosion(ox, oy, big=True))
        self.sounds.play('boss_die')
        for _ in range(boss.drop_count):
            self.powerups.append(PowerUp(
                boss.x + random.randint(-65, 65),
                boss.y + random.randint(-45, 45)
            ))
        if self.mode == 'arcade':
            self.kills += boss.kill_credit
        self.score += boss.score_val
        self.active_bosses = [b for b in self.active_bosses if b is not boss]

        # Levels mode: advance state machine
        if self.mode == 'levels':
            if isinstance(boss, FinalBoss):
                self.state = 'victory'
                self.sounds.play('victory')
                self.effects.set_random_flashes(0)
            elif isinstance(boss, MiniBoss):
                if self.lv_boss_queue:
                    self.lv_wave_phase = 'boss_wait'
                    self.lv_next_boss_timer = 90
                else:
                    self._level_complete()
        # Arcade mode: enrage flag
        if self.mode == 'arcade' and isinstance(boss, Boss):
            self.boss_enraged = False

    def _level_complete(self):
        self.state = 'level_complete'
        self.lv_complete_timer = 180
        self.sounds.play('level_complete')
        self.effects.reset()
        # Unlock next level (save progress)
        if self.lv_idx + 1 < 20:
            self._save_unlocked(self.lv_idx + 1)

    # ── collisions ────────────────────────────────────────────────────────────
    def _collisions(self):
        p_rect = self.player.get_rect()

        # Player bullets vs regular enemies
        for bullet in self.player.bullets:
            if not bullet.active: continue
            br = bullet.get_rect()
            for enemy in self.enemies:
                if enemy.active and br.colliderect(enemy.get_rect()):
                    bullet.active = False
                    if enemy.take_hit():
                        self.score += enemy.score_val; self.kills += 1
                        self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                        self.sounds.play('boom'); enemy.active = False
                        if enemy.should_drop():
                            self.powerups.append(PowerUp(enemy.x, enemy.y))
                    else:
                        self.explosions.append(Explosion(enemy.x, enemy.y))
                    break

        # Player bullets vs active bosses
        for boss in list(self.active_bosses):
            if not boss.active: continue
            old_phase = getattr(boss, 'phase', 1)
            for bullet in self.player.bullets:
                if not bullet.active: continue
                if bullet.get_rect().colliderect(boss.get_rect()):
                    bullet.active = False
                    if boss.take_hit():
                        self._boss_death(boss)
                        break
                    else:
                        self.explosions.append(Explosion(boss.x, boss.y))
            # Enrage check for Dreadnought in arcade mode
            if (self.mode == 'arcade' and isinstance(boss, Boss)
                    and boss.active and boss.phase == 2
                    and old_phase == 1 and not self.boss_enraged):
                self.boss_enraged  = True
                self.enrage_flash  = 35
                self.sounds.play('boss_enrage')

        # Enemy bullets vs player
        all_shooters = list(self.enemies)
        for boss in self.active_bosses:
            if boss.active:
                all_shooters.append(boss)

        for shooter in all_shooters:
            for eb in shooter.bullets:
                if eb.active and eb.get_rect().colliderect(p_rect):
                    eb.active = False
                    shielded  = self.player.has_shield
                    damaged   = self.player.take_damage()
                    if   shielded:  self.sounds.play('shield_break')
                    elif damaged:
                        self.sounds.play('hit')
                        self.explosions.append(Explosion(self.player.x, self.player.y))

        # Boss lasers vs player
        for boss in self.active_bosses:
            if not boss.active: continue
            for lr in self._get_boss_laser_rects(boss):
                if lr and lr.colliderect(p_rect):
                    shielded = self.player.has_shield
                    if self.player.take_damage():
                        if shielded: self.sounds.play('shield_break')
                        else:
                            self.sounds.play('hit')
                            self.explosions.append(Explosion(self.player.x, self.player.y))

        # Enemy ram vs player
        for enemy in self.enemies:
            if enemy.active and enemy.get_rect().colliderect(p_rect):
                enemy.active = False
                self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                self.sounds.play('boom')
                if self.player.take_damage():
                    self.sounds.play('hit')
                    self.explosions.append(Explosion(self.player.x, self.player.y))

        # Player picks up power-ups
        for pu in self.powerups:
            if pu.active and pu.get_rect().colliderect(p_rect):
                pu.active = False
                self.player.apply_powerup(pu.kind)
                self.sounds.play('powerup')

        if self.player.health <= 0:
            self.state = 'game_over'

    # ── Arcade level progression ──────────────────────────────────────────────
    def _check_level_arcade(self):
        if self.kills >= self.kills_level * self.level:
            self.level       += 1
            self.spawn_delay  = max(28, 90 - self.level * 10)
            self._check_boss_spawn_arcade()

    # ── Levels mode state machine ─────────────────────────────────────────────
    def _update_levels_mode(self):
        ts = 0.45 if self.player.slow_active else 1.0

        phase = self.lv_wave_phase

        if phase == 'intro':
            self.lv_intro_timer -= 1
            if self.lv_intro_timer <= 0:
                if LEVELS_DATA[self.lv_idx][1] == 0:
                    # Boss-only wave — go straight to boss_wait
                    self.lv_wave_phase = 'boss_wait'
                    self.lv_next_boss_timer = 60
                else:
                    self.lv_wave_phase = 'normal'

        elif phase == 'normal':
            # Spawn enemies
            if self.lv_spawn_left > 0:
                self.lv_spawn_timer += 1
                if self.lv_spawn_timer >= self.lv_spawn_delay:
                    self._spawn_enemy_levels()
                    self.lv_spawn_left -= 1
                    self.lv_spawn_timer = 0
            else:
                # All spawned; wait for enemies to die
                if not self.enemies and not self.active_bosses:
                    if self.lv_boss_queue:
                        self.lv_wave_phase = 'boss_wait'
                        self.lv_next_boss_timer = 90
                    else:
                        self._level_complete()

        elif phase == 'boss_wait':
            self.lv_next_boss_timer -= 1
            if self.lv_next_boss_timer <= 0:
                if not self.lv_boss_queue:
                    self._level_complete()
                    return
                next_boss = self.lv_boss_queue.pop(0)
                if next_boss == 'FINAL':
                    self.lv_wave_phase = 'final_delay'
                    self.lv_final_delay_timer = 240
                    self.effects.set_vignette(60)
                    self.effects.set_random_flashes(60)
                    self.sounds.play('boss_warning')
                else:  # 'mini'
                    mb = MiniBoss()
                    self.active_bosses.append(mb)
                    self.lv_wave_phase = 'boss'
                    self.warning_text  = "MARAUDER"
                    self.warning_timer = 130
                    self.sounds.play('boss_warning')

        elif phase == 'boss':
            # Wait for all bosses to die
            if not self.active_bosses:
                if self.lv_boss_queue:
                    self.lv_wave_phase = 'boss_wait'
                    self.lv_next_boss_timer = 90
                else:
                    self._level_complete()

        elif phase == 'final_delay':
            self.lv_final_delay_timer -= 1
            # Periodic shake
            if int(self.lv_final_delay_timer) % 20 == 0:
                self.effects.add_shake(3)
            self.effects.set_vignette(60)
            if self.lv_final_delay_timer <= 0:
                fb = FinalBoss()
                self.active_bosses.append(fb)
                self.lv_wave_phase = 'final_boss'
                self.warning_text  = "CRIMSON OVERLORD"
                self.warning_timer = 200
                self.sounds.play('boss_warning')
                self.effects.set_random_flashes(45)

        elif phase == 'final_boss':
            # FinalBoss is in active_bosses; update vignette intensity
            for boss in self.active_bosses:
                if isinstance(boss, FinalBoss):
                    hp_ratio = boss.hp / boss.max_hp
                    vign = (1.0 - hp_ratio) * 220
                    self.effects.set_vignette(vign)
                    if boss.phase == 3:
                        self.effects.set_random_flashes(22)
                    break

    # ── HUD ───────────────────────────────────────────────────────────────────
    def _draw_hud(self):
        if self.mode == 'arcade':
            self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE),  (10, 10))
            self.screen.blit(self.font.render(f"Level: {self.level}", True, YELLOW), (10, 44))
        else:
            self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE),  (10, 10))
            self.screen.blit(self.font.render(f"LEVEL {self.level} / 20", True, YELLOW), (10, 44))

        # Lives
        self.screen.blit(self.font_s.render("Lives:", True, WHITE), (SCREEN_WIDTH-200, 12))
        for i in range(self.player.MAX_HP):
            col = (CYAN if self.player.has_shield else RED) if i < self.player.health else DARK_GRAY
            cx = SCREEN_WIDTH-140+i*28; cy = 22
            pygame.draw.polygon(self.screen, col, [(cx-12,cy+6),(cx+14,cy),(cx-12,cy-6)])

        # Centre top
        if self.active_bosses:
            self._draw_boss_hpbar()
        elif self.mode == 'arcade':
            self._draw_kill_bar()
        else:
            self._draw_score_bar()

        self._draw_active_powerups()

        hint = self.font_s.render("WASD / Arrows — move    SPACE — shoot", True, GRAY)
        self.screen.blit(hint, (SCREEN_WIDTH//2-hint.get_width()//2, SCREEN_HEIGHT-26))

    def _draw_kill_bar(self):
        bx,by,bw,bh = SCREEN_WIDTH//2-80, 8, 160, 14
        thresh  = self.kills_level * self.level
        filled  = min(bw, int(bw*self.kills/thresh)) if thresh else bw
        pygame.draw.rect(self.screen, DARK_GRAY, (bx,by,bw,bh))
        pygame.draw.rect(self.screen, GREEN,     (bx,by,filled,bh))
        pygame.draw.rect(self.screen, GRAY,      (bx,by,bw,bh), 1)
        pt = self.font_s.render(f"{self.kills}/{thresh}", True, WHITE)
        self.screen.blit(pt, pt.get_rect(center=(SCREEN_WIDTH//2, by+bh+10)))

    def _draw_score_bar(self):
        if self.lv_idx >= len(LEVELS_DATA):
            return
        _, _, score_tgt, _ = LEVELS_DATA[self.lv_idx]
        if score_tgt == 0:
            return
        bx,by,bw,bh = SCREEN_WIDTH//2-90, 8, 180, 14
        filled = min(bw, int(bw * self.score / score_tgt)) if score_tgt else bw
        pygame.draw.rect(self.screen, DARK_GRAY, (bx,by,bw,bh))
        pygame.draw.rect(self.screen, CYAN,      (bx,by,filled,bh))
        pygame.draw.rect(self.screen, GRAY,      (bx,by,bw,bh), 1)
        pt = self.font_s.render(f"{self.score}/{score_tgt}", True, WHITE)
        self.screen.blit(pt, pt.get_rect(center=(SCREEN_WIDTH//2, by+bh+10)))

    def _draw_boss_hpbar(self):
        boss = self.active_bosses[-1] if self.active_bosses else None
        if not boss:
            return
        if isinstance(boss, FinalBoss):
            name = "CRIMSON OVERLORD"
            col = (255, 20, 20) if boss.phase == 3 else ((200, 40, 40) if boss.phase == 2 else CRIMSON)
        elif isinstance(boss, Boss):
            name = "DREADNOUGHT"
            col = RED if boss.phase == 2 else ORANGE
        else:
            name = "MARAUDER"
            col = YELLOW

        bw,bh   = 360, 16
        bx, by  = SCREEN_WIDTH//2 - bw//2, 8
        filled  = max(0, int(bw*boss.hp/boss.max_hp))

        pygame.draw.rect(self.screen, DARK_GRAY, (bx,by,bw,bh), border_radius=3)
        pygame.draw.rect(self.screen, col,       (bx,by,filled,bh), border_radius=3)
        pygame.draw.rect(self.screen, GRAY,      (bx,by,bw,bh), 1, border_radius=3)

        phase_txt = f" — Phase {boss.phase}" if isinstance(boss, FinalBoss) else ""
        label = self.font_s.render(f"{name}   {boss.hp} / {boss.max_hp}{phase_txt}", True, WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH//2, by+bh+10)))

    def _draw_active_powerups(self):
        items = []
        if self.player.double_timer > 0: items.append(('2x SHOT',YELLOW,self.player.double_timer,600))
        if self.player.has_shield:       items.append(('SHIELD', CYAN,  1,1))
        if self.player.slow_timer   > 0: items.append(('SLOW',   PURPLE,self.player.slow_timer,300))
        x0, y0 = 10, SCREEN_HEIGHT-58
        for label,col,remaining,total in items:
            bw = 90
            pygame.draw.rect(self.screen,(25,25,35),(x0,y0,bw,26),border_radius=5)
            pygame.draw.rect(self.screen,col,       (x0,y0,bw,26),1,border_radius=5)
            t = self.font_s.render(label, True, col)
            self.screen.blit(t, t.get_rect(center=(x0+bw//2, y0+10)))
            bar = max(0,int(bw*remaining/total)) if total>1 else bw
            pygame.draw.rect(self.screen, col, (x0,y0+23,bar,3))
            x0 += bw+6

    def _draw_warning(self):
        if self.warning_timer <= 0:
            return
        self.warning_timer -= 1
        if (self.warning_timer // 8) % 2 == 0:
            alpha = min(255, self.warning_timer * 4)
            t     = self.font_b.render(f"  {self.warning_text}  ", True, RED)
            s     = pygame.Surface(t.get_size(), pygame.SRCALPHA)
            s.blit(t, (0,0)); s.set_alpha(alpha)
            self.screen.blit(s, s.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2-30)))

    def _draw_slow_tint(self):
        tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        tint.fill((60,30,160,20)); self.screen.blit(tint,(0,0))

    def _draw_enrage_flash(self):
        if self.enrage_flash <= 0: return
        self.enrage_flash -= 1
        alpha = int(130 * self.enrage_flash / 35)
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((255,0,0,alpha)); self.screen.blit(s,(0,0))

    def _draw_level_intro(self):
        if self.lv_wave_phase != 'intro' or self.lv_intro_timer <= 0:
            return
        alpha = min(255, self.lv_intro_timer * 4)
        t1 = self.font_xl.render(f"LEVEL  {self.level}", True, WHITE)
        t2 = self.font.render(f"/ 20", True, YELLOW)
        s1 = pygame.Surface(t1.get_size(), pygame.SRCALPHA)
        s1.blit(t1, (0,0)); s1.set_alpha(alpha)
        s2 = pygame.Surface(t2.get_size(), pygame.SRCALPHA)
        s2.blit(t2, (0,0)); s2.set_alpha(alpha)
        cy = SCREEN_HEIGHT//2
        self.screen.blit(s1, s1.get_rect(center=(SCREEN_WIDTH//2, cy-20)))
        self.screen.blit(s2, s2.get_rect(center=(SCREEN_WIDTH//2, cy+50)))

    def _draw_level_complete(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0,0,0,160)); self.screen.blit(ov,(0,0))
        def ctr(surf, y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))
        ctr(self.font_b.render("LEVEL COMPLETE!", True, GREEN), SCREEN_HEIGHT//2 - 60)
        ctr(self.font.render(f"Score: {self.score}", True, WHITE), SCREEN_HEIGHT//2)
        ctr(self.font_s.render("Preparing next level...", True, GRAY), SCREEN_HEIGHT//2 + 50)

    def _draw_victory(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0,0,0,180)); self.screen.blit(ov,(0,0))
        def ctr(surf, y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))
        ctr(self.font_xl.render("VICTORY!", True, GOLD), SCREEN_HEIGHT//2 - 100)
        ctr(self.font_b.render("All 20 levels cleared!", True, WHITE), SCREEN_HEIGHT//2 - 20)
        ctr(self.font.render(f"Final Score: {self.score}", True, YELLOW), SCREEN_HEIGHT//2 + 60)
        ctr(self.font.render("R — play again   ESC — main menu", True, CYAN), SCREEN_HEIGHT//2 + 120)

    def _draw_game_over(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0,0,0,165)); self.screen.blit(ov,(0,0))
        def ctr(surf,y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2,y)))
        lv_txt = (f"Level: {self.lv_idx+1} / 20" if self.mode == 'levels'
                  else f"Level: {self.level}")
        ctr(self.font_b.render("GAME  OVER",           True, RED),    SCREEN_HEIGHT//2-80)
        ctr(self.font.render(f"Score: {self.score}",   True, WHITE),  SCREEN_HEIGHT//2-10)
        ctr(self.font.render(lv_txt,                   True, YELLOW), SCREEN_HEIGHT//2+35)
        ctr(self.font.render("R — restart   ESC — main menu", True, CYAN), SCREEN_HEIGHT//2+100)

    def _draw_menu(self):
        self.screen.fill(BLACK)
        for star in self.stars:
            star.update(); star.draw(self.screen)

        def ctr(surf, y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))

        title = self.font_xl.render("SPACE SHOOTER", True, CYAN)
        ctr(title, 120)

        # Two mode boxes
        box_w, box_h = 220, 80
        gap = 40
        total = box_w * 2 + gap
        x0 = SCREEN_WIDTH//2 - total//2
        y0 = 260

        modes = [
            ('ARCADE', 'Endless waves, boss every level'),
            ('LEVELS', '20 predefined levels + bosses'),
        ]
        for i, (name, desc) in enumerate(modes):
            bx = x0 + i*(box_w + gap)
            selected = (i == self._menu_sel)
            box_col = CYAN if selected else GRAY
            pygame.draw.rect(self.screen, DARK_GRAY, (bx, y0, box_w, box_h), border_radius=10)
            pygame.draw.rect(self.screen, box_col,   (bx, y0, box_w, box_h), 3, border_radius=10)
            lbl = self.font_b.render(name, True, (WHITE if selected else GRAY))
            self.screen.blit(lbl, lbl.get_rect(center=(bx+box_w//2, y0+box_h//2)))

        # Descriptions
        for i, (name, desc) in enumerate(modes):
            bx = x0 + i*(box_w + gap)
            col = WHITE if i == self._menu_sel else GRAY
            t = self.font_s.render(desc, True, col)
            self.screen.blit(t, t.get_rect(center=(bx+box_w//2, y0+box_h+22)))

        hint = self.font_s.render("A / D or Arrow keys to select    SPACE or ENTER to start", True, GRAY)
        ctr(hint, SCREEN_HEIGHT - 40)

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q: pygame.quit(); sys.exit()

                    # ── Menu ──────────────────────────────────────────────────
                    if self.state == 'menu':
                        if event.key in (pygame.K_LEFT, pygame.K_a):
                            self._menu_sel = (self._menu_sel - 1) % 2
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self._menu_sel = (self._menu_sel + 1) % 2
                        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            if self._menu_sel == 0:  # ARCADE
                                self.mode = 'arcade'
                                self._reset(); self.state = 'playing'
                            else:                    # LEVELS → level select
                                self.mode = 'levels'
                                self._ls_cursor = 0
                                self.state = 'level_select'

                    # ── Level Select ──────────────────────────────────────────
                    elif self.state == 'level_select':
                        cols = 4
                        if event.key in (pygame.K_LEFT,  pygame.K_a):
                            self._ls_cursor = max(0, self._ls_cursor - 1)
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            self._ls_cursor = min(19, self._ls_cursor + 1)
                        elif event.key in (pygame.K_UP,   pygame.K_w):
                            self._ls_cursor = max(0, self._ls_cursor - cols)
                        elif event.key in (pygame.K_DOWN,  pygame.K_s):
                            self._ls_cursor = min(19, self._ls_cursor + cols)
                        elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                            if self._ls_cursor <= self._max_unlocked:
                                self._reset()
                                self.lv_idx = self._ls_cursor   # override after reset
                                self._start_level()
                                self.state = 'playing'
                        elif event.key == pygame.K_ESCAPE:
                            self.state = 'menu'

                    # ── Playing → Pause ───────────────────────────────────────
                    elif self.state == 'playing':
                        if event.key == pygame.K_ESCAPE:
                            self._pause()

                    # ── Paused ────────────────────────────────────────────────
                    elif self.state == 'paused':
                        if event.key in (pygame.K_UP, pygame.K_w):
                            self._pause_sel = (self._pause_sel - 1) % 2
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            self._pause_sel = (self._pause_sel + 1) % 2
                        elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                            if self._pause_sel == 0:
                                self._resume()
                            else:
                                self._reset_to_menu()

                    # ── Game Over / Victory ───────────────────────────────────
                    elif self.state in ('game_over', 'victory'):
                        if event.key == pygame.K_r:
                            # Restart SAME mode (no menu)
                            if self.mode == 'levels':
                                self.lv_idx = 0
                            self._reset(); self.state = 'playing'
                        elif event.key == pygame.K_ESCAPE:
                            self._reset_to_menu()

            if self.state == 'menu':
                self._draw_menu()
                pygame.display.flip(); self.clock.tick(FPS)
                continue

            if self.state == 'level_select':
                self._draw_level_select()
                pygame.display.flip(); self.clock.tick(FPS)
                continue

            if self.state == 'paused':
                self._draw_pause()
                pygame.display.flip(); self.clock.tick(FPS)
                continue

            if self.state == 'playing':
                keys = pygame.key.get_pressed()
                self.player.update(keys)
                if self.player.just_shot: self.sounds.play('shoot')

                ts = 0.45 if self.player.slow_active else 1.0

                if self.mode == 'arcade':
                    # Spawn enemies (pause during big-boss fight)
                    has_big_boss = any(isinstance(b, Boss) for b in self.active_bosses)
                    if not has_big_boss:
                        self.spawn_timer += 1
                        if self.spawn_timer >= self.spawn_delay:
                            self._spawn_enemy_arcade(); self.spawn_timer = 0
                    for e in self.enemies: e.update(ts)
                    self.enemies = [e for e in self.enemies if e.active]
                    for boss in self.active_bosses:
                        if boss.active: boss.update(ts)
                    # Phase check for Dreadnought
                    for boss in self.active_bosses:
                        if (isinstance(boss, Boss) and boss.active
                                and boss.phase == 2 and not self.boss_enraged):
                            self.boss_enraged = True
                            self.enrage_flash = 35
                            self.sounds.play('boss_enrage')
                    self.active_bosses = [b for b in self.active_bosses if b.active]
                    self._check_level_arcade()

                else:  # levels mode
                    self._update_levels_mode()
                    for e in self.enemies: e.update(ts)
                    self.enemies = [e for e in self.enemies if e.active]
                    for boss in self.active_bosses:
                        if boss.active: boss.update(ts, self.effects)
                    self.active_bosses = [b for b in self.active_bosses if b.active]

                for pu in self.powerups: pu.update()
                self.powerups = [pu for pu in self.powerups if pu.active]

                self._collisions()

                for ex in self.explosions: ex.update()
                self.explosions = [ex for ex in self.explosions if ex.active]

                self.effects.update()

            elif self.state == 'level_complete':
                self.lv_complete_timer -= 1
                if self.lv_complete_timer <= 0:
                    self.lv_idx += 1
                    if self.lv_idx >= 20:
                        self.state = 'victory'
                        self.sounds.play('victory')
                    else:
                        self._start_level()
                        self.state = 'playing'

            # ── Draw world to game_surf (shaken) ──────────────────────────────
            self.game_surf.fill(BLACK)
            for star in self.stars:
                star.update(); star.draw(self.game_surf)

            if self.player.slow_active:
                tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                tint.fill((60,30,160,20)); self.game_surf.blit(tint,(0,0))

            for e in self.enemies:  e.draw(self.game_surf)
            for boss in self.active_bosses:
                if boss.active: boss.draw(self.game_surf)
            for pu in self.powerups:   pu.draw(self.game_surf, self.font_s)
            for ex in self.explosions: ex.draw(self.game_surf)
            self.player.draw(self.game_surf)

            # ── Blit game_surf with shake offset ──────────────────────────────
            self.screen.fill(BLACK)
            self.screen.blit(self.game_surf, self.effects.shake_offset)

            # ── HUD and overlays drawn directly to screen (no shake) ──────────
            if self.state in ('playing', 'level_complete', 'victory', 'game_over'):
                self._draw_hud()
                self._draw_warning()
                self._draw_enrage_flash()
                self.effects.draw_vignette(self.screen)
                self.effects.draw_flash(self.screen)

            if self.mode == 'levels' and self.state == 'playing':
                self._draw_level_intro()

            if self.state == 'level_complete':
                self._draw_level_complete()

            if self.state == 'victory':
                self._draw_victory()

            if self.state == 'game_over':
                self._draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

    def _reset_to_menu(self):
        """Clear game state and return to main menu."""
        self.state = 'menu'
        self._pause_surf = None
        self.effects.reset()
        self.active_bosses = []
        self.enemies = []
        self.powerups = []
        self.explosions = []
        self.stars = [Star() for _ in range(180)]

    # ── Save / Load ───────────────────────────────────────────────────────────
    def _load_save(self) -> int:
        """Return max unlocked level index (0-based). 0 = only level 1 available."""
        try:
            with open(self._save_path) as f:
                return int(json.load(f).get('max_unlocked', 0))
        except Exception:
            return 0

    def _save_unlocked(self, idx: int):
        """Persist highest unlocked level index."""
        self._max_unlocked = max(self._max_unlocked, idx)
        try:
            with open(self._save_path, 'w') as f:
                json.dump({'max_unlocked': self._max_unlocked}, f)
        except Exception:
            pass

    # ── Pause ─────────────────────────────────────────────────────────────────
    def _pause(self):
        """Freeze game and enter pause state."""
        self.state = 'paused'
        self._pause_sel = 0
        # Capture current game frame for the dimmed background
        self._pause_surf = self.game_surf.copy()

    def _resume(self):
        self.state = 'playing'
        self._pause_surf = None

    def _draw_pause(self):
        """Dim the frozen game frame and show pause menu."""
        if self._pause_surf:
            self.screen.blit(self._pause_surf, (0, 0))
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160)); self.screen.blit(ov, (0, 0))

        def ctr(surf, y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))

        ctr(self.font_b.render("PAUSED", True, CYAN), SCREEN_HEIGHT//2 - 90)

        options = ["Resume", "Main Menu"]
        for i, label in enumerate(options):
            col  = WHITE if i == self._pause_sel else GRAY
            bg   = (30, 80, 100) if i == self._pause_sel else DARK_GRAY
            bw, bh = 260, 54
            bx = SCREEN_WIDTH//2 - bw//2
            by = SCREEN_HEIGHT//2 - 10 + i * 70
            pygame.draw.rect(self.screen, bg,   (bx, by, bw, bh), border_radius=8)
            pygame.draw.rect(self.screen, col,  (bx, by, bw, bh), 2, border_radius=8)
            t = self.font.render(label, True, col)
            self.screen.blit(t, t.get_rect(center=(SCREEN_WIDTH//2, by + bh//2)))

        hint = self.font_s.render("↑↓ — select    ENTER / ESC — confirm", True, GRAY)
        ctr(hint, SCREEN_HEIGHT//2 + 170)

    # ── Level Select ──────────────────────────────────────────────────────────
    def _draw_level_select(self):
        self.screen.fill(BLACK)
        for star in self.stars: star.update(); star.draw(self.screen)

        def ctr(surf, y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))
        ctr(self.font_b.render("SELECT LEVEL", True, CYAN), 50)

        cols, rows = 4, 5
        cw, ch = 186, 88
        gx = 8   # gap x
        gy = 6   # gap y
        grid_w = cols * cw + (cols-1) * gx
        grid_h = rows * ch + (rows-1) * gy
        ox = (SCREEN_WIDTH  - grid_w) // 2
        oy = 95

        for idx in range(20):
            col_i = idx % cols
            row_i = idx // cols
            x = ox + col_i * (cw + gx)
            y = oy + row_i * (ch + gy)

            unlocked  = idx <= self._max_unlocked
            selected  = idx == self._ls_cursor
            ld = LEVELS_DATA[idx]
            score_tgt = ld[2]
            bosses    = ld[3]

            # Background colour
            if not unlocked:
                bg = (25, 25, 25)
                border = (70, 70, 70)
            elif selected:
                bg = (15, 55, 80)
                border = CYAN
            else:
                bg = (30, 30, 45)
                border = (90, 90, 120)

            pygame.draw.rect(self.screen, bg,     (x, y, cw, ch), border_radius=6)
            pygame.draw.rect(self.screen, border, (x, y, cw, ch), 2, border_radius=6)

            if unlocked:
                lbl = self.font.render(f"LEVEL {idx+1}", True, WHITE if not selected else CYAN)
                self.screen.blit(lbl, lbl.get_rect(center=(x+cw//2, y+20)))
                if score_tgt > 0:
                    sc = self.font_s.render(f"{score_tgt:,} pts", True, YELLOW)
                    self.screen.blit(sc, sc.get_rect(center=(x+cw//2, y+42)))
                # Boss indicator
                if bosses:
                    n_mini  = bosses.count('mini')
                    has_fin = 'FINAL' in bosses
                    if has_fin:
                        bi = self.font_s.render("★ FINAL BOSS", True, RED)
                    else:
                        bi = self.font_s.render("🟡 " + "×".join(["M"] * n_mini), True, GOLD)
                    self.screen.blit(bi, bi.get_rect(center=(x+cw//2, y+62)))
            else:
                lk = self.font.render(f"{idx+1}", True, (70, 70, 70))
                self.screen.blit(lk, lk.get_rect(center=(x+cw//2, y+28)))
                lo = self.font_s.render("LOCKED", True, (80, 80, 80))
                self.screen.blit(lo, lo.get_rect(center=(x+cw//2, y+54)))

        hint = self.font_s.render("Arrows — navigate    ENTER/SPACE — start    ESC — back", True, GRAY)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 20)))


if __name__ == "__main__":
    Game().run()
