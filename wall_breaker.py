import pygame as pg
import sys
import os
import random
import time
import math  # 標準のmathモジュールを追加

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- 定数設定 ---
SCREEN_WIDTH = 800  # 画面の横幅
SCREEN_HEIGHT = 600 # 画面の縦幅
PADDLE_WIDTH = 100 # ラケットの横幅
PADDLE_HEIGHT = 20 # ラケットの縦幅
BALL_RADIUS = 10   # ボールの半径
BLOCK_WIDTH = 75   # ブロックの横幅
BLOCK_HEIGHT = 30  # ブロックの縦幅
FPS = 60           # フレームレート

# 色の定義 (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# ゲームオーバーラインのY座標（ラケットの少し上）
GAME_OVER_LINE = SCREEN_HEIGHT - 150

# パーティクルの設定
PARTICLE_LIFETIME = 30  # パーティクルの寿命（フレーム数）
PARTICLE_SPEED = 5     # パーティクルの初期速度

# --- サウンド設定 ---
def load_sounds():
    """効果音をロード"""
    pg.mixer.init()  # mixer（音声周り）の初期化
    sounds = {}
    try:
        # ブロック破壊音
        break_sound = pg.mixer.Sound("sound/break.mp3")
        break_sound.set_volume(0.4)  # 音量を40%に設定
        sounds["break"] = break_sound
        
        # ゲームオーバー音
        defeat_sound = pg.mixer.Sound("sound/defeat.mp3")
        defeat_sound.set_volume(0.5)  # 音量を50%に設定
        sounds["defeat"] = defeat_sound
        
    except Exception as e:
        print(f"効果音ファイルの読み込みに失敗しました: {e}")
    
    return sounds

# --- クラス定義 ---

class Particle:
    """パーティクルエフェクトのクラス"""
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.lifetime = PARTICLE_LIFETIME
        # ランダムな方向と速度を設定
        angle = random.uniform(0, 2 * math.pi)  # ランダムな角度（0-2π）
        speed = random.uniform(2, PARTICLE_SPEED)
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.size = random.randint(2, 4)  # パーティクルのサイズ

    def update(self):
        """パーティクルの位置と寿命を更新"""
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        # 徐々に透明になる
        alpha = int(255 * (self.lifetime / PARTICLE_LIFETIME))
        self.color = (*self.color[:3], alpha)
        return self.lifetime > 0

    def draw(self, screen):
        """パーティクルを描画"""
        particle_surface = pg.Surface((self.size * 2, self.size * 2), pg.SRCALPHA)
        pg.draw.circle(particle_surface, self.color, (self.size, self.size), self.size)
        screen.blit(particle_surface, (int(self.x) - self.size, int(self.y) - self.size))

class Paddle:
    """ ラケット（操作対象）のクラス """
    def __init__(self):
        # ラケットのRectを画面中央下に作成
        self.rect = pg.Rect(
            (SCREEN_WIDTH - PADDLE_WIDTH) // 2, 
            SCREEN_HEIGHT - PADDLE_HEIGHT - 20, 
            PADDLE_WIDTH, 
            PADDLE_HEIGHT
        )
        self.speed = 10 # 移動速度

    def update(self, keys):
        """ キー入力に基づきラケットを移動 """
        if keys[pg.K_a]:
            self.rect.move_ip(-self.speed, 0)
        if keys[pg.K_d]:
            self.rect.move_ip(self.speed, 0)
        
        # 画面外に出ないように制限
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def draw(self, screen):
        """ ラケットを画面に描画 """
        pg.draw.rect(screen, BLUE, self.rect)

class Ball:
    """ ボールのクラス """
    def __init__(self):
        # ... (既存の rect, vx, vy, speed の設定はそのまま) ...
        self.rect = pg.Rect(
            SCREEN_WIDTH // 2 - BALL_RADIUS, 
            SCREEN_HEIGHT - PADDLE_HEIGHT - 50, 
            BALL_RADIUS * 2, 
            BALL_RADIUS * 2
        )
        self.vx = random.choice([-5, 5])
        self.vy = -5
        self.speed = 5

        # --- ▼ アイテム効果用の変数を追加 ▼ ---
        self.penetrate = False # 貫通状態か
        self.penetrate_timer = 0 # 貫通の持続時間タイマー
        self.is_large = False  # 巨大化状態か
        self.large_timer = 0   # 巨大化の持続時間タイマー
        # --- ▲ -------------------------- ▲ ---

    def update(self, paddle, blocks, particles, break_sound=None):
        """ ボールの移動と衝突判定 """
        self.rect.move_ip(self.vx, self.vy)

        # ... (壁との衝突判定 (上) はそのまま) ...
        if self.rect.top < 0:
            self.vy *= -1 
            self.rect.top = 0

        # ... (壁との衝突判定 (左・右) はそのまま) ...
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.vx *= -1
            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH

        # ラケットとの衝突判定
        if self.rect.colliderect(paddle.rect):
            self.vy *= -1 
            self.rect.bottom = paddle.rect.top 
            
            center_diff = self.rect.centerx - paddle.rect.centerx
            self.vx = (center_diff / (PADDLE_WIDTH / 2)) * self.speed
            if abs(self.vx) < 1:
                self.vx = 1 if self.vx >= 0 else -1

            # --- ▼ 貫通アイテムの効果がラケットで切れるようにする（任意）▼ ---
            # if self.penetrate:
            #     self.set_penetrate(False) # ラケットに当たったら貫通解除する場合
            # --- ▲ --------------------------------------------------- ▲ ---


        # ブロックとの衝突判定
        collided_block = self.rect.collidelist(blocks) 
        if collided_block != -1: 
            block = blocks.pop(collided_block) # 衝突したブロックをリストから削除
            
            # --- ▼ 貫通状態の処理 ▼ ---
            if self.penetrate:
                # 貫通状態なら反射しない (ブロックは消えるだけ)
                pass 
            else:
                # 通常時は反射する
                self.vy *= -1
            # --- ▲ ------------------ ▲ ---
            
            # --- ▼ 戻り値を変更 ▼ ---
            # パーティクルエフェクトの生成（衝突したブロックの中心から）
            for _ in range(10):  # 10個のパーティクルを生成
                particles.append(
                    Particle(block.centerx, block.centery, (*WHITE, 255))
                )
            
            # 効果音の再生
            if break_sound is not None:
                break_sound.play()
            
            return True, block # ブロックに当たったことと、壊したブロックを返す
            # --- ▲ ---------------- ▲ ---
        
        # --- ▼ アイテムタイマーの更新 ▼ ---
        if self.is_large:
            self.large_timer -= 1
            if self.large_timer <= 0:
                self.set_size(False) # 通常サイズに戻す
        
        if self.penetrate:
            self.penetrate_timer -= 1
            if self.penetrate_timer <= 0:
                self.set_penetrate(False) # 通常状態に戻す
        # --- ▲ ---------------------- ▲ ---
        
        # --- ▼ 戻り値を変更 ▼ ---
        return False, None # ブロックに当たらなかった
        # --- ▲ ---------------- ▲ ---

    def draw(self, screen):
        """ ボールを画面に描画 (円形) """
        # --- ▼ 状態に応じて描画を変更 ▼ ---
        radius = BALL_RADIUS * 2 if self.is_large else BALL_RADIUS
        color = GREEN if self.penetrate else WHITE
        pg.draw.circle(screen, color, self.rect.center, radius)
        # --- ▲ ------------------------- ▲ ---

    def is_out_of_bounds(self):
        """ ボールが画面下に落ちたか判定 """
        return self.rect.top > SCREEN_HEIGHT

    # --- ▼ アイテム効果を適用するメソッドを追加 ▼ ---
    def set_penetrate(self, value):
        """ 貫通状態を設定する """
        self.penetrate = value
        if value:
            self.penetrate_timer = 60 * 10 # 10秒間持続 (FPS=60)
        else:
            self.penetrate_timer = 0

    def set_size(self, is_large):
        """ ボールのサイズを変更する """
        # サイズ変更時に中心がズレないように調整
        center = self.rect.center
        
        self.is_large = is_large
        if is_large:
            # 巨大化
            self.rect.width = BALL_RADIUS * 4
            self.rect.height = BALL_RADIUS * 4
            self.large_timer = 60 * 10 # 10秒間持続 (FPS=60)
        else:
            # 通常化
            self.rect.width = BALL_RADIUS * 2
            self.rect.height = BALL_RADIUS * 2
        
        self.rect.center = center # 中心を再設定

class Block(pg.Rect):
    """ ブロックのクラス (pg.Rectを継承) """
    def __init__(self, x, y, color):
        super().__init__(x, y, BLOCK_WIDTH, BLOCK_HEIGHT)
        self.color = color

    def draw(self, screen):
        """ ブロックを画面に描画 """
        pg.draw.rect(screen, self.color, self)


class Item2(pg.Rect):
    """ アイテムのクラス (pg.Rectを継承) """
    def __init__(self, x, y, item_type):
        self.item_type = item_type # "penetrate"（貫通） or "large_ball"（巨大化）
        
        # アイテムの種類によって色を変える
        if self.item_type == "penetrate":
            self.color = GREEN # 貫通アイテムは緑
        elif self.item_type == "large_ball":
            self.color = YELLOW # 巨大化アイテムは黄
        
        self.speed = 3 # 落下速度
        
        # アイテムのサイズ
        item_width = 20
        item_height = 20
        # (x, y) はブロックの中心座標として受け取り、アイテムの中心に設定する
        super().__init__(x - item_width // 2, y - item_height // 2, item_width, item_height)

    def update(self):
        """ アイテムを下に移動させる """
        self.move_ip(0, self.speed)

    def draw(self, screen):
        """ アイテムを描画する（色分け） """
        pg.draw.rect(screen, self.color, self)

    def check_collision(self, paddle_rect):
        """ ラケットとの衝突を判定する """
        return self.colliderect(paddle_rect)

# --- メイン処理 ---

def create_block_row(y: int) -> list[Block]:
    """
    指定のy座標にブロックの新しい1行を生成
    引数 y: ブロックのy座標
    戻り値: 生成したブロックのリスト
    """
    new_blocks = []
    for x in range(10):  # 10列
        block = Block(
            x * (BLOCK_WIDTH + 5) + 20,  # X座標 (隙間5px, 左マージン20px)
            y,  # 指定されたY座標
            WHITE  # 白色で統一
        )
        new_blocks.append(block)
    return new_blocks

def move_blocks_down(blocks: list[Block]) -> bool:
    """
    全てのブロックを1段下に移動
    引数 blocks: ブロックのリスト
    戻り値: ゲームオーバー（ブロックが下限に達したか）
    """
    for block in blocks:
        block.y += BLOCK_HEIGHT + 5  # ブロック1個分（+隙間）下に移動
        if block.bottom >= GAME_OVER_LINE:  # ゲームオーバーライン
            return True
    return False

def main():
    """ メインのゲームループ """
    # ... (初期化、画面設定、フォント設定などはそのまま) ...
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pg.display.set_caption("ブロック崩し")
    clock = pg.time.Clock()
    font = pg.font.Font(None, 50) 
    
    # 効果音のロード
    sounds = load_sounds()

    # オブジェクトのインスタンス化
    paddle = Paddle()
    ball = Ball()
    blocks = []
    particles = []  # パーティクルのリストを追加
    # --- ▼ アイテムリストを追加 ▼ ---
    items = [] # 落下中のアイテムを管理するリスト
    # --- ▲ ------------------- ▲ ---
    
    # ... (ブロックの配置 はそのまま) ...
    block_colors = [RED, YELLOW, GREEN, BLUE]
    for y in range(4): 
        blocks.extend(create_block_row(y * (BLOCK_HEIGHT + 5) + 30))

    score = 0
    game_over = False
    game_clear = False
    
    # ブロック移動の管理用変数
    last_drop_time = time.time()  # 最後にブロックを落とした時刻
    DROP_INTERVAL = 10  # ブロックを落とす間隔（秒）

    # ゲームループ
    while True:
        # ... (イベント処理、リスタート処理はそのまま) ...
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r and (game_over or game_clear):
                    main() 
                    return

        if not game_over and not game_clear:
            keys = pg.key.get_pressed()
            
            # オブジェクトの更新
            paddle.update(keys)
            
            # --- ▼ Ball.updateの戻り値の変更に対応 ▼ ---
            block_hit, destroyed_block = ball.update(paddle, blocks, particles, sounds.get("break"))

            if block_hit: # ブロックに当たったら
                score += 10 # スコア加算

                # --- ▼ アイテムドロップ処理 ▼ ---
                # 30%の確率でアイテムをドロップ (確率は調整可能)
                if random.random() < 0.3: 
                    # 貫通か巨大化をランダムに選ぶ
                    item_type = random.choice(["penetrate", "large_ball"])
                    # 壊れたブロックの中心位置にアイテムを生成
                    item = Item2(destroyed_block.centerx, destroyed_block.centery, item_type)
                    items.append(item)
                # --- ▲ ----------------------- ▲ ---
            # --- ▲ -------------------------------- ▲ ---

            # --- ▼ アイテムの更新とラケットとの衝突判定 ▼ ---
            for item in items[:]: # リストのコピーをイテレート（削除処理のため）
                item.update() # アイテムを落下
                
                # ラケットと衝突したら
                if item.check_collision(paddle.rect):
                    if item.item_type == "penetrate":
                        ball.set_penetrate(True) # ボールを貫通状態に
                    elif item.item_type == "large_ball":
                        ball.set_size(True) # ボールを巨大化
                    
                    items.remove(item) # アイテムをリストから削除
                
                # 画面外に出たら削除
                elif item.top > SCREEN_HEIGHT:
                    items.remove(item)
            # --- ▲ -------------------------------------- ▲ ---

            # パーティクルの更新
            particles[:] = [p for p in particles if p.update()]

            # ゲームオーバー判定
            if ball.is_out_of_bounds():
                game_over = True
                # ゲームオーバー効果音を再生
                if sounds.get("defeat"):
                    sounds["defeat"].play()
            
            # ブロックの移動と新しい行の追加（5秒ごと）
            current_time = time.time()
            if current_time - last_drop_time >= DROP_INTERVAL:
                # 全ブロックを1段下に移動
                if move_blocks_down(blocks):
                    game_over = True  # ブロックが下限に達したらゲームオーバー
                    # ゲームオーバー効果音を再生
                    if sounds.get("defeat"):
                        sounds["defeat"].play()
                else:
                    # 最上段に新しい行を追加
                    blocks.extend(create_block_row(30))  # 上端のY座標（30px）
                last_drop_time = current_time

            # ゲームクリア判定
            if not blocks: # ブロックがなくなったら
                game_clear = True

        # 描画処理
        screen.fill(BLACK) 
        
        # ゲームオーバーラインを描画（点線で表示）
        dash_length = 15  # 点線の長さ
        gap_length = 10   # 点線の間隔
        for x in range(0, SCREEN_WIDTH, dash_length + gap_length):
            pg.draw.line(screen, RED, (x, GAME_OVER_LINE), (x + dash_length, GAME_OVER_LINE), 2)
            
        paddle.draw(screen)
        ball.draw(screen)
        for block in blocks:
            block.draw(screen)
        
        # パーティクルの描画
        for particle in particles:
            particle.draw(screen)

        # --- ▼ アイテムの描画 ▼ ---
        for item in items:
            item.draw(screen)
        # --- ▲ ----------------- ▲ ---

        # ... (スコア表示、ゲームオーバー / クリア表示 はそのまま) ...
        score_text = font.render(f"SCORE: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        if game_over:
            msg_text = font.render("GAME OVER", True, RED)
            screen.blit(msg_text, (SCREEN_WIDTH // 2 - msg_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            msg_text2 = font.render("Press 'R' to Restart", True, WHITE)
            screen.blit(msg_text2, (SCREEN_WIDTH // 2 - msg_text2.get_width() // 2, SCREEN_HEIGHT // 2))
        
        if game_clear:
            msg_text = font.render("GAME CLEAR!", True, YELLOW)
            screen.blit(msg_text, (SCREEN_WIDTH // 2 - msg_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            msg_text2 = font.render("Press 'R' to Restart", True, WHITE)
            screen.blit(msg_text2, (SCREEN_WIDTH // 2 - msg_text2.get_width() // 2, SCREEN_HEIGHT // 2))


        pg.display.update()
        clock.tick(FPS)

if __name__ == "__main__":
    main()