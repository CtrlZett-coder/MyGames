import pygame
import random
import sys
import math

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
BLACK     = (0,   0,   0)
WHITE     = (255, 255, 255)
RED       = (220, 50,  50)
DARK_RED  = (140, 0,   0)
YELLOW    = (255, 220, 0)
CYAN      = (0,   200, 255)
ORANGE    = (255, 140, 0)
GREEN     = (50,  200, 50)
GRAY      = (150, 150, 150)
DARK_GRAY = (40,  40,  40)
BLUE      = (50,  100, 255)
PURPLE    = (160, 30,  220)
GOLD      = (200, 160, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  SOUND MANAGER  — procedural audio via numpy, gracefully silent without it
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
                'shoot':       self._sine(sr, 820,  0.07, decay=35, vol=0.22),
                'boom':        self._noise(sr, 0.30, decay=9,  vol=0.55),
                'hit':         self._sine(sr, 200,  0.18, decay=12, vol=0.45),
                'powerup':     self._rising(sr, 440, 880, 0.35, vol=0.40),
                'shield_break':self._sine(sr, 300,  0.25, decay=8,  vol=0.50),
                'boss_warning':self._sine(sr, 110,  0.60, decay=3,  vol=0.60),
                'boss_enrage': self._enrage(sr),
                'boss_die':    self._noise(sr, 0.60, decay=4, vol=0.70),
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
        return self._to_sound(np.random.uniform(-1,1,n) * np.exp(-decay*t) * vol * 32767)

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

    def _play_ambient(self, sr=22050):
        dur = 5.0
        n, t = int(sr*dur), np.linspace(0, dur, int(sr*dur), False)
        wave = (np.sin(2*np.pi*55*t)*0.30 + np.sin(2*np.pi*82*t)*0.20
              + np.sin(2*np.pi*110*t)*0.12 + np.sin(2*np.pi*165*t)*0.08)
        wave *= 0.7 + 0.3*np.sin(2*np.pi*0.4*t)
        fl = int(sr*0.5)
        fade = np.ones(n); fade[:fl]=np.linspace(0,1,fl); fade[-fl:]=np.linspace(1,0,fl)
        wave = (wave*fade*32767*0.45).astype(np.int16)
        snd = pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([wave,wave])))
        snd.set_volume(0.35); snd.play(-1)

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
#  MINI-BOSS — Marauder (gold, 8 HP, fan shots, appears at level 3 / 6 / 9…)
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

    def update(self, time_scale=1.0):
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
                for ang in range(162, 203, 8):   # 6-bullet fan
                    self.bullets.append(EnemyBullet(self.x-self.W//2, self.y, ang))

        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def take_hit(self) -> bool: self.hp -= 1; return self.hp <= 0

    def draw(self, surf):
        x, y = int(self.x), int(self.y)

        # Wings (large swept)
        pygame.draw.polygon(surf, (150,120,0), [(x-36,y-10),(x-8,y-38),(x+22,y-10)])
        pygame.draw.polygon(surf, (150,120,0), [(x-36,y+10),(x-8,y+38),(x+22,y+10)])
        # Body hull
        pygame.draw.ellipse(surf, GOLD,   (x-36,y-23,72,46))
        pygame.draw.ellipse(surf, YELLOW, (x-18,y-13,36,26))
        # Gun ports (left side)
        for dy in (-16,-6,4,14):
            pygame.draw.rect  (surf, GRAY,   (x-46,y+dy-3,18,6))
            pygame.draw.circle(surf, ORANGE, (x-46,y+dy), 3)
        # Spinning core
        pygame.draw.circle(surf, YELLOW, (x,y), 13)
        pygame.draw.circle(surf, WHITE,  (x,y), 7)
        for i in range(4):
            a = math.radians(self.move_timer*3 + i*90)
            pygame.draw.circle(surf, (255,200,0), (x+int(10*math.cos(a)), y+int(10*math.sin(a))), 3)
        # HP bar (above ship)
        bw = 80; filled = max(0, int(bw*self.hp/self.max_hp))
        pygame.draw.rect(surf, DARK_GRAY, (x-40,y-42,bw,8))
        pygame.draw.rect(surf, YELLOW,    (x-40,y-42,filled,8))
        pygame.draw.rect(surf, GRAY,      (x-40,y-42,bw,8), 1)

        for b in self.bullets: b.draw(surf)

    def get_rect(self): return pygame.Rect(self.x-self.W//2, self.y-self.H//2, self.W, self.H)


# ══════════════════════════════════════════════════════════════════════════════
#  BIG BOSS — Dreadnought (dark red, 25 HP, 2 phases + laser, level 5/10/15…)
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
        # laser
        self.laser_active= False
        self.laser_timer = 0.0
        self.laser_cd    = 0.0

    def update(self, time_scale=1.0):
        if self.x > self._target_x:
            self.x -= 2.5 * time_scale
        else:
            self.entering = False
            self.move_timer += time_scale
            amp = 195 if self.phase == 2 else 155
            spd = 0.020 if self.phase == 2 else 0.014
            self.y = SCREEN_HEIGHT//2 + math.sin(self.move_timer*spd)*amp
            self.y = max(60, min(SCREEN_HEIGHT-60, self.y))

        # Phase transition check handled externally (so enrage flash fires once)
        if not self.entering:
            delay = 38 if self.phase == 2 else 58
            self.shoot_timer -= time_scale
            if self.shoot_timer <= 0:
                self.shoot_timer = delay
                angs = range(151,213,8) if self.phase==2 else range(155,210,11)
                for ang in angs:
                    self.bullets.append(EnemyBullet(self.x-self.W//2, self.y, ang))

            # Laser (phase 2)
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

    def draw(self, surf):
        x, y = int(self.x), int(self.y)

        # ── Laser beam ──
        lr = self.get_laser_rect()
        if lr:
            # flicker only in first 20 frames (wind-up) and last 20 (fade)
            flickering = self.laser_timer > self.LASER_DURATION-20 or self.laser_timer < 20
            if not flickering or (int(self.laser_timer)//3)%2:
                pygame.draw.rect(surf, (255,40,40),  lr)
                pygame.draw.rect(surf, (255,160,160), pygame.Rect(lr.x,lr.y+4,lr.w,4))
                pygame.draw.rect(surf, WHITE,         pygame.Rect(lr.x,lr.y+5,lr.w,2))

        # ── Wing panels ──
        col_wing = (90,10,10) if self.phase==2 else (70,10,10)
        pygame.draw.polygon(surf, col_wing, [(x-52,y-28),(x-14,y-68),(x+32,y-22)])
        pygame.draw.polygon(surf, col_wing, [(x-52,y+28),(x-14,y+68),(x+32,y+22)])

        # ── Hull ──
        hull_col = (100,15,15) if self.phase==2 else (72,12,12)
        pygame.draw.ellipse(surf, hull_col,    (x-57,y-38,114,78))
        pygame.draw.ellipse(surf, (155,28,28), (x-28,y-19,58,40))

        # ── Gun barrels (5 ports) ──
        for dy in (-30,-15,0,15,30):
            pygame.draw.rect  (surf, GRAY,   (x-66,y+dy-4,24,8))
            pygame.draw.circle(surf, ORANGE, (x-64,y+dy), 4)

        # ── Core ──
        core_col  = (255,40,40)   if self.phase==2 else ORANGE
        inner_col = (255,200,0)   if self.phase==2 else YELLOW
        pygame.draw.circle(surf, core_col,  (x,y), 22)
        pygame.draw.circle(surf, inner_col, (x,y), 12)
        pygame.draw.circle(surf, WHITE,     (x,y), 5)

        # Phase-2 rotating energy ring
        if self.phase == 2:
            for i in range(8):
                a = math.radians(self.move_timer*4 + i*45)
                rx,ry = x+int(22*math.cos(a)), y+int(22*math.sin(a))
                pygame.draw.circle(surf,(255,80,80),(rx,ry),3)

        # ── HP bar ──
        bw = 110; filled = max(0, int(bw*self.hp/self.max_hp))
        bar_col = RED if self.phase==2 else ORANGE
        pygame.draw.rect(surf, DARK_GRAY, (x-55,y-58,bw,10))
        pygame.draw.rect(surf, bar_col,   (x-55,y-58,filled,10))
        pygame.draw.rect(surf, GRAY,      (x-55,y-58,bw,10), 1)

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
    WEIGHTS = {
        1: {'fighter':8,'scout':2,'heavy':0},
        2: {'fighter':6,'scout':3,'heavy':1},
        3: {'fighter':5,'scout':3,'heavy':2},
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("🚀 Space Shooter")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock  = pygame.time.Clock()
        self.font   = pygame.font.Font(None, 36)
        self.font_b = pygame.font.Font(None, 74)
        self.font_s = pygame.font.Font(None, 24)
        self.sounds = SoundManager()
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
        self.state       = 'playing'
        # Boss state
        self.miniboss:  MiniBoss | None = None
        self.boss:      Boss     | None = None
        self.bosses_spawned: set        = set()
        self.boss_enraged               = False
        self.warning_text               = ""
        self.warning_timer              = 0
        self.enrage_flash               = 0

    # ── spawning ──────────────────────────────────────────────────────────────
    def _spawn_enemy(self):
        lv = min(self.level, 3)
        w  = self.WEIGHTS[lv]
        self.enemies.append(Enemy(random.choices(list(w.keys()), list(w.values()))[0]))

    def _check_boss_spawn(self):
        """Trigger boss at level 5/10/15… (big) or 3/6/9… (mini, not big-boss levels)."""
        if self.boss or self.miniboss:
            return
        lv = self.level
        if lv in self.bosses_spawned:
            return
        if lv % 5 == 0:
            self.bosses_spawned.add(lv)
            self.enemies.clear()
            self.boss          = Boss()
            self.boss_enraged  = False
            self.warning_text  = "⚠  D R E A D N O U G H T  ⚠"
            self.warning_timer = 190
            self.sounds.play('boss_warning')
        elif lv % 3 == 0:
            self.bosses_spawned.add(lv)
            self.miniboss      = MiniBoss()
            self.warning_text  = "⚠  M A R A U D E R  ⚠"
            self.warning_timer = 130
            self.sounds.play('boss_warning')

    def _boss_death(self, boss):
        """Common cleanup when any boss is killed."""
        count = 5 if isinstance(boss, Boss) else 3
        for _ in range(count):
            ox = boss.x + random.randint(-55,55)
            oy = boss.y + random.randint(-40,40)
            self.explosions.append(Explosion(ox, oy, big=True))
        self.sounds.play('boss_die')
        for _ in range(boss.drop_count):
            self.powerups.append(PowerUp(
                boss.x + random.randint(-65,65),
                boss.y + random.randint(-45,45)
            ))
        self.kills += boss.kill_credit
        if isinstance(boss, Boss):
            self.boss = None; self.boss_enraged = False
        else:
            self.miniboss = None

    # ── collisions ────────────────────────────────────────────────────────────
    def _collisions(self):
        p_rect = self.player.get_rect()

        # ── Player bullets vs regular enemies ─────────────────────────────
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

        # ── Player bullets vs mini-boss ────────────────────────────────────
        if self.miniboss and self.miniboss.active:
            for bullet in self.player.bullets:
                if not bullet.active: continue
                if bullet.get_rect().colliderect(self.miniboss.get_rect()):
                    bullet.active = False
                    if self.miniboss.take_hit():
                        self.score += self.miniboss.score_val
                        self._boss_death(self.miniboss)
                    else:
                        self.explosions.append(Explosion(self.miniboss.x, self.miniboss.y))

        # ── Player bullets vs big boss ─────────────────────────────────────
        if self.boss and self.boss.active:
            old_phase = self.boss.phase
            for bullet in self.player.bullets:
                if not bullet.active: continue
                if bullet.get_rect().colliderect(self.boss.get_rect()):
                    bullet.active = False
                    if self.boss.take_hit():
                        self.score += self.boss.score_val
                        self._boss_death(self.boss)
                    else:
                        self.explosions.append(Explosion(self.boss.x, self.boss.y))
            # Enrage transition (fires once)
            if (self.boss and self.boss.active
                    and self.boss.phase == 2 and old_phase == 1
                    and not self.boss_enraged):
                self.boss_enraged  = True
                self.enrage_flash  = 35
                self.sounds.play('boss_enrage')

        # ── Enemy bullets vs player ────────────────────────────────────────
        all_shooters = list(self.enemies)
        if self.miniboss and self.miniboss.active: all_shooters.append(self.miniboss)
        if self.boss     and self.boss.active:     all_shooters.append(self.boss)

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

        # ── Boss laser vs player ───────────────────────────────────────────
        if self.boss and self.boss.active:
            lr = self.boss.get_laser_rect()
            if lr and lr.colliderect(p_rect):
                shielded = self.player.has_shield
                if self.player.take_damage():
                    if shielded: self.sounds.play('shield_break')
                    else:
                        self.sounds.play('hit')
                        self.explosions.append(Explosion(self.player.x, self.player.y))

        # ── Enemy ram vs player ────────────────────────────────────────────
        for enemy in self.enemies:
            if enemy.active and enemy.get_rect().colliderect(p_rect):
                enemy.active = False
                self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                self.sounds.play('boom')
                if self.player.take_damage():
                    self.sounds.play('hit')
                    self.explosions.append(Explosion(self.player.x, self.player.y))

        # ── Player picks up power-ups ──────────────────────────────────────
        for pu in self.powerups:
            if pu.active and pu.get_rect().colliderect(p_rect):
                pu.active = False
                self.player.apply_powerup(pu.kind)
                self.sounds.play('powerup')

        if self.player.health <= 0:
            self.state = 'game_over'

    # ── level progression ─────────────────────────────────────────────────────
    def _check_level(self):
        if self.kills >= self.kills_level * self.level:
            self.level       += 1
            self.spawn_delay  = max(28, 90 - self.level * 10)
            self._check_boss_spawn()

    # ── HUD ───────────────────────────────────────────────────────────────────
    def _draw_hud(self):
        self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE),  (10, 10))
        self.screen.blit(self.font.render(f"Level: {self.level}", True, YELLOW), (10, 44))

        # Lives
        self.screen.blit(self.font_s.render("Lives:", True, WHITE), (SCREEN_WIDTH-200, 12))
        for i in range(self.player.MAX_HP):
            col = (CYAN if self.player.has_shield else RED) if i < self.player.health else DARK_GRAY
            cx = SCREEN_WIDTH-140+i*28; cy = 22
            pygame.draw.polygon(self.screen, col, [(cx-12,cy+6),(cx+14,cy),(cx-12,cy-6)])

        # Centre top: kill bar or boss HP bar
        if self.boss or self.miniboss:
            self._draw_boss_hpbar()
        else:
            self._draw_kill_bar()

        # Active power-ups
        self._draw_active_powerups()

        # Controls hint (bottom)
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

    def _draw_boss_hpbar(self):
        boss    = self.boss or self.miniboss
        is_big  = isinstance(boss, Boss)
        name    = "DREADNOUGHT" if is_big else "MARAUDER"
        col     = RED if (is_big and boss.phase==2) else (ORANGE if is_big else YELLOW)

        bw,bh   = 360, 16
        bx, by  = SCREEN_WIDTH//2 - bw//2, 8
        filled  = max(0, int(bw*boss.hp/boss.max_hp))

        pygame.draw.rect(self.screen, DARK_GRAY, (bx,by,bw,bh), border_radius=3)
        pygame.draw.rect(self.screen, col,       (bx,by,filled,bh), border_radius=3)
        pygame.draw.rect(self.screen, GRAY,      (bx,by,bw,bh), 1, border_radius=3)

        label = self.font_s.render(f"{name}   {boss.hp} / {boss.max_hp}", True, WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH//2, by+bh+10)))

        if is_big and boss.phase == 2:
            ph2 = self.font_s.render("— PHASE 2 —", True, RED)
            self.screen.blit(ph2, ph2.get_rect(center=(SCREEN_WIDTH//2, by+bh+26)))

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
            t     = self.font_b.render(self.warning_text, True, RED)
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

    def _draw_game_over(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0,0,0,165)); self.screen.blit(ov,(0,0))
        def ctr(surf,y): self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2,y)))
        ctr(self.font_b.render("GAME  OVER",           True, RED),    SCREEN_HEIGHT//2-80)
        ctr(self.font.render(f"Score: {self.score}",   True, WHITE),  SCREEN_HEIGHT//2-10)
        ctr(self.font.render(f"Level: {self.level}",   True, YELLOW), SCREEN_HEIGHT//2+35)
        ctr(self.font.render("R — restart   Q — quit", True, CYAN),   SCREEN_HEIGHT//2+100)

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q: pygame.quit(); sys.exit()
                    if event.key == pygame.K_r and self.state == 'game_over': self._reset()

            if self.state == 'playing':
                keys = pygame.key.get_pressed()
                self.player.update(keys)
                if self.player.just_shot: self.sounds.play('shoot')

                ts = 0.45 if self.player.slow_active else 1.0

                # Spawn regular enemies (pause during big-boss fight)
                if not self.boss:
                    self.spawn_timer += 1
                    if self.spawn_timer >= self.spawn_delay:
                        self._spawn_enemy(); self.spawn_timer = 0

                for e in self.enemies:    e.update(ts)
                self.enemies = [e for e in self.enemies if e.active]

                if self.miniboss and self.miniboss.active: self.miniboss.update(ts)
                if self.boss     and self.boss.active:     self.boss.update(ts)
                # Phase-2 check for boss (must happen AFTER boss.update so phase may change)
                if (self.boss and self.boss.active
                        and self.boss.phase == 2 and not self.boss_enraged):
                    self.boss_enraged = True
                    self.enrage_flash = 35
                    self.sounds.play('boss_enrage')

                for pu in self.powerups: pu.update()
                self.powerups = [pu for pu in self.powerups if pu.active]

                self._collisions()

                for ex in self.explosions: ex.update()
                self.explosions = [ex for ex in self.explosions if ex.active]

                self._check_level()

            # ── Draw ──────────────────────────────────────────────────────────
            self.screen.fill(BLACK)
            for star in self.stars: star.update(); star.draw(self.screen)

            if self.player.slow_active: self._draw_slow_tint()

            for e  in self.enemies:  e.draw(self.screen)
            if self.miniboss and self.miniboss.active: self.miniboss.draw(self.screen)
            if self.boss     and self.boss.active:     self.boss.draw(self.screen)

            for pu in self.powerups:   pu.draw(self.screen, self.font_s)
            for ex in self.explosions: ex.draw(self.screen)
            self.player.draw(self.screen)

            self._draw_hud()
            self._draw_warning()
            self._draw_enrage_flash()

            if self.state == 'game_over': self._draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
