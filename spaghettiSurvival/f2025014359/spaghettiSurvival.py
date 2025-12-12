# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk
import time
import math
import random
import pygame
import os

# 게임 설정 및 상수
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480
FPS = 60
DELAY = 1000 // FPS

# 물리/속도 관련
GRAVITY = 0.6
JUMP_FORCE = -12
SPEED_FORWARD = 8
SPEED_BACKWARD = 6
MONSTER_SPEED = 6

# 게임 밸런스
MONSTER_MAX_HP = 1000
PLAYER_MAX_AMMO = 50
BOMB_MAX_COUNT = 3
BOMB_DAMAGE = 20
RELOAD_TIME = 3.0
STUN_TIME = 3.0
DAMAGE_PER_BULLET = 1
BOMB_SPEED = 12
EXPLOSION_RADIUS = 80
EXPLOSION_DURATION = 0.5

class Game:
    def __init__(self):
        self.window = Tk()
        self.window.title("스파게티 괴물 죽이기")
        self.window.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        self.window.resizable(0, 0)
        
        self.canvas = Canvas(self.window, bg="white", width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        self.canvas.pack(fill=BOTH, expand=True)

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.keys = set()
        self.mouse_pos = [0, 0]
        self.mouse_pressed = {'left': False, 'right': False}
        
        self.window.bind("<KeyPress>", self.key_press)
        self.window.bind("<KeyRelease>", self.key_release)
        self.window.bind("<Motion>", self.mouse_move)
        self.window.bind("<ButtonPress-1>", lambda e: self.mouse_btn(e, True, 'left'))
        self.window.bind("<ButtonRelease-1>", lambda e: self.mouse_btn(e, False, 'left'))
        self.window.bind("<ButtonPress-3>", lambda e: self.mouse_btn(e, True, 'right'))
        self.window.bind("<ButtonRelease-3>", lambda e: self.mouse_btn(e, False, 'right'))
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.snd_gun = None
        self.snd_reload = None
        self.snd_bomb = None

        pygame.init()
        pygame.mixer.init()
            
        bgm_path = os.path.join(self.base_path, "bgm.mp3")
        gun_path = os.path.join(self.base_path, "gun.mp3")
        reload_path = os.path.join(self.base_path, "reload.mp3")
        bomb_path = os.path.join(self.base_path, "bomb.mp3")

        if os.path.exists(bgm_path): pygame.mixer.music.load(bgm_path)
        if os.path.exists(gun_path): self.snd_gun = pygame.mixer.Sound(gun_path)
        if os.path.exists(reload_path): self.snd_reload = pygame.mixer.Sound(reload_path)
        if os.path.exists(bomb_path): self.snd_bomb = pygame.mixer.Sound(bomb_path)

        self.state = "MENU"
        self.running = True
        
        self.menu_options = ["시작", "도움말", "기록", "종료"]
        self.menu_index = 0
        
        self.bullets = []
        self.bombs = [] 
        self.obstacles = []

        self.menu_bg_image = None
        menu_bg_path = os.path.join(self.base_path, "menu_bg.png")
        if os.path.exists(menu_bg_path):
            bg_img = Image.open(menu_bg_path)
            self.menu_bg_image = ImageTk.PhotoImage(bg_img)

        self.ingame_bg_image = None
        ingame_bg_path = os.path.join(self.base_path, "ingame_bg.png")
        if os.path.exists(ingame_bg_path):
            ig_bg = Image.open(ingame_bg_path)
            ig_bg = ig_bg.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.LANCZOS)
            self.ingame_bg_image = ImageTk.PhotoImage(ig_bg)

        self.monster_img = None
        monster_path = os.path.join(self.base_path, "spaghetti.png")
        if os.path.exists(monster_path):
            load_m_img = Image.open(monster_path)
            load_m_img = load_m_img.resize((120, 120), Image.LANCZOS)
            self.monster_img = ImageTk.PhotoImage(load_m_img)

        self.player_img_right = None
        self.player_img_left = None
        player_path = os.path.join(self.base_path, "player.png")
        if os.path.exists(player_path):
            load_p_img = Image.open(player_path)
            load_p_img = load_p_img.resize((40, 40), Image.LANCZOS)
            self.player_img_right = ImageTk.PhotoImage(load_p_img.transpose(Image.FLIP_LEFT_RIGHT))
            self.player_img_left = ImageTk.PhotoImage(load_p_img)

        self.reset_game_vars()
        self.main_loop()

    def reset_game_vars(self):
        self.p_x = 400
        self.p_y = 350
        self.p_vx = 0
        self.p_vy = 0
        self.on_ground = False
        self.facing = "right"
        
        self.ammo = PLAYER_MAX_AMMO
        self.bomb_count = BOMB_MAX_COUNT
        self.is_reloading = False
        self.reload_start_time = 0
        self.last_shot_time = 0

        self.m_x = 100
        self.m_y = 320 
        self.m_hp = MONSTER_MAX_HP
        self.m_stunned = False
        self.m_stun_end_time = 0

        self.scroll_x = 0
        self.obstacle_timer = 0
        
        self.start_time = 0
        self.end_time_str = ""
        
        self.bullets = []
        self.bombs = [] 
        self.obstacles = []

    def main_loop(self):
        while self.running:
            try:
                start_t = time.time()
                self.canvas.delete("all")

                if self.state == "MENU":
                    self.update_menu()
                elif self.state == "PLAY":
                    self.update_play()
                elif self.state == "HELP":
                    self.update_help()
                elif self.state == "RANK":
                    self.update_rank()
                elif self.state == "GAME_OVER" or self.state == "CLEAR":
                    self.update_end_screen()

                self.window.update()
                
                elapsed = time.time() - start_t
                wait = max(0, (1.0/FPS) - elapsed)
                time.sleep(wait)

            except TclError:
                break

    def key_press(self, event):
        self.keys.add(event.keysym)
        
        if self.state == "MENU":
            if event.keysym == "Up":
                self.menu_index = (self.menu_index - 1) % len(self.menu_options)
            elif event.keysym == "Down":
                self.menu_index = (self.menu_index + 1) % len(self.menu_options)
            elif event.keysym == "space" or event.keysym == "Return":
                self.execute_menu()
        
        elif (self.state == "RANK" or self.state == "HELP") and event.keysym == "Escape":
            self.state = "MENU"
        
        elif (self.state == "GAME_OVER" or self.state == "CLEAR") and event.keysym == "space":
             if pygame.mixer.get_init():
                 pygame.mixer.music.stop()
             self.state = "MENU"

    def key_release(self, event):
        if event.keysym in self.keys:
            self.keys.remove(event.keysym)

    def mouse_move(self, event):
        self.mouse_pos = [event.x, event.y]

    def mouse_btn(self, event, pressed, btn_type):
        self.mouse_pressed[btn_type] = pressed
        if pressed and btn_type == 'right' and self.state == "PLAY":
            self.use_bomb()

    def on_close(self):
        self.running = False
        self.window.destroy()
        pygame.quit()

    def execute_menu(self):
        if self.menu_index == 0:
            self.reset_game_vars()
            self.start_time = time.time()
            self.state = "PLAY"

            bgm_path = os.path.join(self.base_path, "bgm.mp3")
            if pygame.mixer.get_init() and os.path.exists(bgm_path):
                pygame.mixer.music.play(-1)

        elif self.menu_index == 1:
            self.state = "HELP"
            
        elif self.menu_index == 2:
            self.state = "RANK"
            
        elif self.menu_index == 3:
            self.on_close()

    def save_record(self, time_str):
        try:
            rank_path = os.path.join(self.base_path, "ranking.txt")
            with open(rank_path, "a", encoding='utf-8') as f:
                f.write(time_str + "\n")
        except:
            pass

    def load_records(self):
        records = []
        rank_path = os.path.join(self.base_path, "ranking.txt")
        if os.path.exists(rank_path):
            with open(rank_path, "r", encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    records.append(line.strip())
        records.sort()
        return records[:10]

    def update_menu(self):
        if self.menu_bg_image:
            self.canvas.create_image(0, 0, image=self.menu_bg_image, anchor=NW)
        else:
             self.canvas.create_rectangle(0,0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#f0f0f0")

        start_y = 180
        for i, option in enumerate(self.menu_options):
            text_color = "white"
            shadow_color = "black"
            prefix = ""
            
            if i == self.menu_index:
                text_color = "red"
                prefix = "▶ "
            
            text_content = prefix + option
            x_pos = 100
            y_pos = start_y + i * 60
            self.canvas.create_text(x_pos + 2, y_pos + 2, text=text_content, font=("Times", 30, "bold"), fill=shadow_color, anchor="w")
            self.canvas.create_text(x_pos, y_pos, text=text_content, font=("Times", 30, "bold"), fill=text_color, anchor="w")

    def update_help(self):
        self.canvas.create_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#FFE4B5")
        
        self.canvas.create_text(400, 60, text="< 게임 조작법 >", font=("Times", 35, "bold"), fill="black")
        
        instructions = [
            ("이동", "W, A, D"),
            ("점프", "Space Bar"),
            ("공격 (총)", "마우스 왼쪽 클릭"),
            ("특수 공격 (폭탄)", "마우스 오른쪽 클릭 (횟수 제한)"),
            ("재장전", "S 키"),
        ]
        
        start_y = 150
        for i, (action, key) in enumerate(instructions):
            self.canvas.create_text(250, start_y + i*50, text=action, font=("Times", 20, "bold"), anchor="e", fill="#8B4513")
            self.canvas.create_text(280, start_y + i*50, text=":", font=("Times", 20, "bold"), anchor="center")
            self.canvas.create_text(310, start_y + i*50, text=key, font=("Times", 20), anchor="w", fill="black")

        self.canvas.create_text(400, 420, text="Press ESC to return", font=("Times", 15), fill="gray")

    def update_rank(self):
        self.canvas.create_rectangle(0,0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#eee")
        self.canvas.create_text(400, 50, text="순 위", font=("Times", 30, "bold"))
        records = self.load_records()
        for i, rec in enumerate(records):
            self.canvas.create_text(400, 120 + i*30, text=f"{i+1}. {rec}", font=("Times", 15))
        self.canvas.create_text(400, 450, text="Press ESC to return", fill="gray")

    def update_end_screen(self):
        bg_color = "black" if self.state == "GAME_OVER" else "#87CEEB"
        msg = "GAME OVER" if self.state == "GAME_OVER" else "CLEAR!"
        sub_msg = "스파게티에게 잡혔습니다." if self.state == "GAME_OVER" else f"기록: {self.end_time_str}"
        self.canvas.create_rectangle(0,0, SCREEN_WIDTH, SCREEN_HEIGHT, fill=bg_color)
        self.canvas.create_text(400, 200, text=msg, font=("Times", 50, "bold"), fill="white")
        self.canvas.create_text(400, 300, text=sub_msg, font=("Times", 20), fill="white")
        self.canvas.create_text(400, 400, text="Press SPACE to Menu", fill="white")

    def update_play(self):
        current_time = time.time()

        if self.mouse_pos[0] < self.p_x:
            self.facing = 'left'
        else:
            self.facing = 'right'

        move_x = 0
        if 'a' in self.keys or 'A' in self.keys: move_x -= 1
        if 'd' in self.keys or 'D' in self.keys: move_x += 1
        
        if ('w' in self.keys or 'W' in self.keys or 'space' in self.keys) and self.on_ground:
            self.p_vy = JUMP_FORCE
            self.on_ground = False
        
        current_speed = 0
        if move_x != 0:
            same_dir = (move_x > 0 and self.facing == 'right') or (move_x < 0 and self.facing == 'left')
            current_speed = SPEED_FORWARD if same_dir else SPEED_BACKWARD

        actual_move = move_x * current_speed
        
        if actual_move > 0 and self.p_x >= 400:
            scroll_amt = actual_move
            self.scroll_x += scroll_amt
            self.m_x -= scroll_amt
            for obs in self.obstacles:
                obs['x'] -= scroll_amt
            for bomb in self.bombs:
                bomb['x'] -= scroll_amt
                bomb['target_x'] -= scroll_amt
        else:
            self.p_x += actual_move
            self.p_x = max(0, min(self.p_x, SCREEN_WIDTH))

        self.p_vy += GRAVITY
        self.p_y += self.p_vy
        
        ground_y = 400
        if self.p_y >= ground_y:
            self.p_y = ground_y
            self.p_vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        if random.randint(0, 100) < 5: 
             h = random.randint(1, 9) * 10 
             self.obstacles.append({'x': SCREEN_WIDTH + 50, 'h': h, 'w': 30})

        dead_obs = []
        player_rect = [self.p_x - 15, self.p_y - 40, self.p_x + 15, self.p_y]
        
        for obs in self.obstacles:
            if obs['x'] < -50:
                dead_obs.append(obs)
                continue
            
            obs_l = obs['x']
            obs_r = obs['x'] + obs['w']
            obs_t = ground_y - obs['h']
            obs_b = ground_y
            
            if (player_rect[2] > obs_l and player_rect[0] < obs_r and 
                player_rect[3] > obs_t and player_rect[1] < obs_b):
                
                overlap_left = player_rect[2] - obs_l         
                overlap_right = obs_r - player_rect[0]        
                overlap_top = player_rect[3] - obs_t          
                overlap_bottom = obs_b - player_rect[1]       
                
                min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

                if min_overlap == overlap_top:
                    if self.p_vy >= 0: 
                        self.p_y = obs_t
                        self.p_vy = 0
                        self.on_ground = True
                
                elif min_overlap == overlap_bottom:
                    self.p_y = obs_b + 40 
                    self.p_vy = 0
                    
                elif min_overlap == overlap_left:
                    self.p_x = obs_l - 15
                    
                elif min_overlap == overlap_right:
                    self.p_x = obs_r + 15

        for do in dead_obs:
            self.obstacles.remove(do)

        if self.m_stunned:
            if current_time > self.m_stun_end_time:
                self.m_stunned = False
        else:
            if self.m_x < self.p_x:
                self.m_x += MONSTER_SPEED
            elif self.m_x > self.p_x:
                self.m_x -= MONSTER_SPEED

        if 's' in self.keys or 'S' in self.keys:
            if not self.is_reloading and self.ammo < PLAYER_MAX_AMMO:
                self.is_reloading = True
                self.reload_start_time = current_time
                if self.snd_reload: self.snd_reload.play()
        
        if self.is_reloading:
            if current_time - self.reload_start_time >= RELOAD_TIME:
                self.ammo = PLAYER_MAX_AMMO
                self.is_reloading = False

        if self.mouse_pressed['left'] and not self.is_reloading and self.ammo > 0:
            if current_time - self.last_shot_time > 0.1:
                self.fire_bullet()
                self.ammo -= 1
                self.last_shot_time = current_time

        dead_bullets = []
        monster_hit_radius = 60 
        for b in self.bullets:
            b['x'] += math.cos(b['angle']) * 15
            b['y'] += math.sin(b['angle']) * 15
            
            dist_to_m = math.sqrt((b['x'] - self.m_x)**2 + (b['y'] - self.m_y)**2)
            
            if dist_to_m < monster_hit_radius:
                self.m_hp -= DAMAGE_PER_BULLET
                dead_bullets.append(b)
                if self.m_hp <= 0:
                    self.game_clear(current_time)
                    return
            elif b['x'] < 0 or b['x'] > SCREEN_WIDTH or b['y'] < 0 or b['y'] > SCREEN_HEIGHT:
                dead_bullets.append(b)
        
        for db in dead_bullets:
            if db in self.bullets:
                self.bullets.remove(db)

        dead_bombs = []
        for bomb in self.bombs:
            if bomb['exploded']:
                if current_time - bomb['explode_time'] > EXPLOSION_DURATION:
                    dead_bombs.append(bomb)
            else:
                bomb['x'] += math.cos(bomb['angle']) * BOMB_SPEED
                bomb['y'] += math.sin(bomb['angle']) * BOMB_SPEED

                dist_to_m = math.sqrt((bomb['x'] - self.m_x)**2 + (bomb['y'] - self.m_y)**2)
                if dist_to_m < 70:
                    bomb['exploded'] = True
                    bomb['explode_time'] = current_time
                    if self.snd_bomb: self.snd_bomb.play()
                    
                    self.m_stunned = True
                    self.m_stun_end_time = time.time() + STUN_TIME
                    self.m_hp -= BOMB_DAMAGE
                    if self.m_hp <= 0:
                        self.game_clear(current_time)
                        return

                else:
                    dist_to_target = math.sqrt((bomb['x'] - bomb['target_x'])**2 + (bomb['y'] - bomb['target_y'])**2)
                    if dist_to_target < BOMB_SPEED:
                        bomb['exploded'] = True
                        bomb['explode_time'] = current_time
                        bomb['x'] = bomb['target_x']
                        bomb['y'] = bomb['target_y']
                        
                        dist_splash = math.sqrt((bomb['x'] - self.m_x)**2 + (bomb['y'] - self.m_y)**2)
                        if self.snd_bomb: self.snd_bomb.play()
                        
                        if dist_splash < EXPLOSION_RADIUS + 60:
                            self.m_stunned = True
                            self.m_stun_end_time = time.time() + STUN_TIME
                            self.m_hp -= BOMB_DAMAGE
                            if self.m_hp <= 0:
                                self.game_clear(current_time)
                                return

        for db in dead_bombs:
            if db in self.bombs:
                self.bombs.remove(db)

        p_center_y = self.p_y - 20
        dist_to_monster = math.sqrt((self.p_x - self.m_x)**2 + (p_center_y - self.m_y)**2)
        
        if dist_to_monster < 80: 
            self.state = "GAME_OVER"
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()

        self.draw_game()

    def fire_bullet(self):
        dx = self.mouse_pos[0] - self.p_x
        dy = self.mouse_pos[1] - (self.p_y - 20)
        angle = math.atan2(dy, dx)
        self.bullets.append({'x': self.p_x, 'y': self.p_y - 20, 'angle': angle})
        if self.snd_gun: self.snd_gun.play()

    def use_bomb(self):
        if self.bomb_count > 0:
            self.bomb_count -= 1
            
            target_x = self.m_x
            target_y = self.m_y
            
            start_x = self.p_x
            start_y = self.p_y - 20
            
            dx = target_x - start_x
            dy = target_y - start_y
            angle = math.atan2(dy, dx)
            
            self.bombs.append({
                'x': start_x, 'y': start_y,
                'target_x': target_x, 'target_y': target_y,
                'angle': angle,
                'exploded': False,
                'explode_time': 0
            })

    def game_clear(self, current_time):
        self.state = "CLEAR"
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

        duration = current_time - self.start_time
        mins = int(duration // 60)
        secs = int(duration % 60)
        mils = int((duration - int(duration)) * 100)
        self.end_time_str = f"{mins:02d}분 {secs:02d}초 {mils:02d}"
        self.save_record(self.end_time_str)

    def draw_game(self):

        if self.ingame_bg_image:
            bg_speed_factor = 0.5
            shift = (self.scroll_x * bg_speed_factor) % SCREEN_WIDTH
            self.canvas.create_image(-shift, 0, image=self.ingame_bg_image, anchor=NW)
            self.canvas.create_image(-shift + SCREEN_WIDTH, 0, image=self.ingame_bg_image, anchor=NW)
        else:
            self.canvas.create_rectangle(0,0, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#87CEEB")

        self.canvas.create_rectangle(0, 400, SCREEN_WIDTH, SCREEN_HEIGHT, fill="#228B22")
        
        for obs in self.obstacles:
            self.canvas.create_rectangle(obs['x'], 400 - obs['h'], obs['x'] + obs['w'], 400, fill="black", outline="white")

        if self.monster_img:
            self.canvas.create_image(self.m_x, self.m_y, image=self.monster_img)
        else:
            m_color = "gray" if self.m_stunned else "red"
            self.canvas.create_oval(self.m_x - 60, self.m_y - 60, self.m_x + 60, self.m_y + 60, fill=m_color, tags="monster")

        self.canvas.create_text(self.m_x, self.m_y - 80, text=f"HP: {self.m_hp}", fill="red", font="bold")
        if self.m_stunned:
             self.canvas.create_text(self.m_x, self.m_y, text="기절!", fill="red")

        if self.player_img_right and self.player_img_left:
            img_to_draw = self.player_img_right if self.facing == 'right' else self.player_img_left
            self.canvas.create_image(self.p_x, self.p_y - 20, image=img_to_draw)
        else:
             p_color = "blue"
             self.canvas.create_oval(self.p_x - 20, self.p_y - 40, self.p_x + 20, self.p_y, fill=p_color, tags="player")

        for b in self.bullets:
            self.canvas.create_line(b['x'], b['y'], b['x'] + math.cos(b['angle'])*10, b['y'] + math.sin(b['angle'])*10, fill="yellow", width=3)
            
        for bomb in self.bombs:
            if not bomb['exploded']:
                self.canvas.create_oval(bomb['x'] - 10, bomb['y'] - 10, bomb['x'] + 10, bomb['y'] + 10, fill="black")

        bar_width = 600
        hp_percent = max(0, self.m_hp / MONSTER_MAX_HP)
        self.canvas.create_rectangle(100, 20, 100 + bar_width, 35, fill="gray")
        self.canvas.create_rectangle(100, 20, 100 + (bar_width * hp_percent), 35, fill="red")
        
        self.canvas.create_text(600, 60, text=f"폭탄: {self.bomb_count} / {BOMB_MAX_COUNT}", font=("Times", 15, "bold"), anchor="w", fill="black")
        
        ammo_color = "black"
        ammo_text = f"총알: {self.ammo} / {PLAYER_MAX_AMMO}"
        if self.is_reloading:
            ammo_color = "red"
            ammo_text = "재장전 중..."
        
        self.canvas.create_text(600, 85, text=ammo_text, font=("Times", 15, "bold"), anchor="w", fill=ammo_color)

if __name__ == "__main__":
    ShootingGame = Game()