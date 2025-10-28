import pygame as pg
import sys
import os
import random

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
# ★担当アイテムの色
PINK = (255, 192, 203) # ラケット巨大化
ORANGE = (255, 165, 0) # 残機増加
CYAN = (0, 255, 255)   # ボール増加

# --- クラス定義 ---

class Paddle:
    """ ラケット（操作対象）のクラス """
    def __init__(self):
        self.rect = pg.Rect(
            (SCREEN_WIDTH - PADDLE_WIDTH) // 2, 
            SCREEN_HEIGHT - PADDLE_HEIGHT - 20, 
            PADDLE_WIDTH, 
            PADDLE_HEIGHT
        )
        self.speed = 10

    def update(self, keys):
        """ キー入力に基づきラケットを移動 """
        if keys[pg.K_a]:
            self.rect.move_ip(-self.speed, 0)
        if keys[pg.K_d]:
            self.rect.move_ip(self.speed, 0)
        
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def draw(self, screen):
        """ ラケットを画面に描画 """
        pg.draw.rect(screen, BLUE, self.rect)

class Ball:
    """ ボールのクラス (基本機能) """
    def __init__(self):
        self.rect = pg.Rect(
            SCREEN_WIDTH // 2 - BALL_RADIUS, 
            SCREEN_HEIGHT - PADDLE_HEIGHT - 50, 
            BALL_RADIUS * 2, 
            BALL_RADIUS * 2
        )
        self.vx = random.choice([-5, 5])
        self.vy = -5
        self.speed = 5
        
        # (貫通・爆弾などのフラグは、
        #  マージ時にここに追加していく)

    def update(self, paddle, blocks):
        """ ボールの移動と衝突判定 """
        self.rect.move_ip(self.vx, self.vy)

        # 壁との衝突 (上)
        if self.rect.top < 0:
            self.vy *= -1 
            self.rect.top = 0

        # 壁との衝突 (左・右)
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.vx *= -1 
            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH

        # ラケットとの衝突
        if self.rect.colliderect(paddle.rect):
            self.vy *= -1 
            self.rect.bottom = paddle.rect.top 
            
            # ラケット幅の変動に対応 (item1)
            center_diff = self.rect.centerx - paddle.rect.centerx
            self.vx = (center_diff / (paddle.rect.width / 2)) * self.speed 
            if abs(self.vx) < 1:
                self.vx = 1 if self.vx >= 0 else -1

        # ブロックとの衝突
        collided_block = self.rect.collidelist(blocks) 
        if collided_block != -1: 
            # 壊したブロックのインスタンスを返す
            block = blocks.pop(collided_block) 
            self.vy *= -1 
            return block # 壊したブロックを返す
        
        return None # 何にも当たらなかった

    def draw(self, screen):
        """ ボールを画面に描画 (円形) """
        # (マージ時に、貫通(緑)や巨大化(半径変更)をここに反映)
        pg.draw.circle(screen, WHITE, self.rect.center, BALL_RADIUS)

    def is_out_of_bounds(self):
        """ ボールが画面下に落ちたか判定 """
        return self.rect.top > SCREEN_HEIGHT


class Block(pg.Rect):
    """ ブロックのクラス (pg.Rectを継承) """
    def __init__(self, x, y, color):
        super().__init__(x, y, BLOCK_WIDTH, BLOCK_HEIGHT)
        self.color = color
        # (ここに hp や is_item_block などの属性が追加される)

    def draw(self, screen):
        """ ブロックを画面に描画 """
        pg.draw.rect(screen, self.color, self)

class item1:
    """
    担当アイテムの効果発動とタイマー管理を行うクラス
    (ラケット巨大化、残機増加、ボール増加)
    """
    def __init__(self, paddle_original_width):
        self.paddle_extend_active = False
        self.extend_start_time = 0
        self.EXTEND_DURATION = 10000 # 10秒 = 10000 ms
        self.original_width = paddle_original_width
        self.extended_width = int(paddle_original_width * 1.5) 

    def activate(self, effect_name: str, balls: list, paddle: Paddle) -> int:
        """
        アイテム名(effect_name)に基づき、効果を発動する。
        :return: 残機(life)の増減量 (int)
        """
        if effect_name == "extend_paddle": # ラケット巨大化
            self.paddle_extend_active = True
            self.extend_start_time = pg.time.get_ticks()
            center_x = paddle.rect.centerx
            paddle.rect.width = self.extended_width
            paddle.rect.centerx = center_x
            return 0 

        elif effect_name == "increase_life": # 残機増加
            return 1 # mainループ側でlifeを1増やす

        elif effect_name == "increase_ball": # ボール増加
            balls.append(Ball()) 
            return 0
        
        return 0 # 担当外のアイテム

    def update(self, paddle: Paddle):
        """
        毎フレーム呼び出す。ラケット巨大化のタイマーを管理する。
        """
        if not self.paddle_extend_active:
            return
        current_time = pg.time.get_ticks()
        elapsed_time = current_time - self.extend_start_time
        if elapsed_time > self.EXTEND_DURATION:
            self.paddle_extend_active = False
            center_x = paddle.rect.centerx
            paddle.rect.width = self.original_width
            paddle.rect.centerx = center_x

class Item(pg.Rect):
    """ 落下アイテムの共通クラス (pg.Rectを継承) """
    def __init__(self, x, y, item_type):
        self.item_type = item_type # "extend_paddle" など
        
        # 担当アイテムの色分け
        if self.item_type == "extend_paddle":
            self.color = PINK 
        elif self.item_type == "increase_life":
            self.color = ORANGE 
        elif self.item_type == "increase_ball":
            self.color = CYAN 
        else:
            self.color = WHITE # (他の担当アイテム用)
            
        self.speed = 3 # 落下速度
        item_width = 20
        item_height = 20
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
def main():
    """ メインのゲームループ """
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Pygameの初期化
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pg.display.set_caption("ウォールブレイカー（担当分 落下テスト版）")
    clock = pg.time.Clock()
    font = pg.font.Font(None, 50) 
    
    # --- オブジェクトのインスタンス化 ---
    paddle = Paddle()
    
    # ボールはリスト管理
    balls = [Ball()] 
    
    # 落下アイテムリスト
    items = [] 
    
    blocks = []
    
    # 担当アイテムマネージャー
    item_manager_ishii = item1(PADDLE_WIDTH) 

    # ブロックの配置
    block_colors = [RED, YELLOW, GREEN, BLUE]
    for y in range(4): 
        for x in range(10): 
            block = Block(
                x * (BLOCK_WIDTH + 5) + 20,
                y * (BLOCK_HEIGHT + 5) + 30,
                block_colors[y % len(block_colors)]
            )
            blocks.append(block)

    score = 0
    life = 3
    game_over = False
    game_clear = False
    
    # (ダミー) 担当分のアイテムのみ抽選
    MY_ITEM_TYPES = [
        "extend_paddle", # 担当分
        "increase_life", # 担当分
        "increase_ball", # 担当分
    ]

    # --- ゲームループ ---
    while True:
        # --- イベント処理 ---
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r and (game_over or game_clear):
                    main() # ゲームリスタート
                    return
                
                # --- デバッグキー (コメントアウト) ---
                # '1'キーでラケット巨大化アイテムを強制ドロップ
                # if event.key == pg.K_1:
                #     item = Item(SCREEN_WIDTH // 2, 0, "extend_paddle")
                #     items.append(item)
                # '2'キーで残機増加アイテムを強制ドロップ
                # elif event.key == pg.K_2:
                #     item = Item(SCREEN_WIDTH // 2, 0, "increase_life")
                #     items.append(item)
                # '3'キーでボール増加アイテムを強制ドロップ
                # elif event.key == pg.K_3:
                #     item = Item(SCREEN_WIDTH // 2, 0, "increase_ball")
                #     items.append(item)

        if not game_over and not game_clear:
            keys = pg.key.get_pressed()
            paddle.update(keys)

            # すべてのボールを更新
            for ball in balls[:]: 
                # ボールの更新。戻り値(壊したブロック)を受け取る
                destroyed_block = ball.update(paddle, blocks)
                
                if destroyed_block: # ブロックに当たったら
                    score += 10 # スコア加算

                    # --- アイテムドロップ処理 (抽選処理のダミー) ---
                    # 30%の確率で担当アイテムをドロップ
                    if random.random() < 0.3: 
                        item_type = random.choice(MY_ITEM_TYPES)
                        
                        # 壊れたブロックの中心位置にアイテムを生成
                        item = Item(destroyed_block.centerx, destroyed_block.centery, item_type)
                        items.append(item)
            

            # --- 落下アイテムの更新とラケットとの衝突判定 ---
            for item in items[:]: # リストのコピーをイテレート
                item.update() # アイテムを落下
                
                # ラケットと衝突したら
                if item.check_collision(paddle.rect):
                    item_type = item.item_type # "extend_paddle" などを取得
                    
                    # --- 担当分の効果発動 ---
                    life_change = item_manager_ishii.activate(item_type, balls, paddle)
                    life += life_change # 残機を更新
                    
                    # (ここに他の担当者の効果発動ロジックも追加していく)
                    # if item_type == "penetrate":
                    #    for ball in balls: ball.set_penetrate(True) 

                    items.remove(item) # アイテムをリストから削除
                
                # 画面外に出たら削除
                elif item.top > SCREEN_HEIGHT:
                    items.remove(item)
            
            # ラケット巨大化タイマーの更新
            item_manager_ishii.update(paddle)
            
            # 画面外に落ちたボールをリストから削除
            balls = [ball for ball in balls if not ball.is_out_of_bounds()]

            # ボールが0個になったら残機を減らす
            if not balls and not game_clear: 
                life -= 1
                if life > 0:
                    balls.append(Ball()) 
                    paddle = Paddle() 
                else:
                    if not game_over: 
                        game_over = True 

            # ゲームクリア判定
            if not blocks:
                game_clear = True

        # --- 描画処理 ---
        screen.fill(BLACK)
        paddle.draw(screen)
        
        for ball in balls: # すべてのボールを描画
            ball.draw(screen)
        for block in blocks:
            block.draw(screen)
        for item in items: # すべてのアイテムを描画
            item.draw(screen)

        # スコアと残機表示
        score_text = font.render(f"SCORE: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        life_text = font.render(f"LIFE: {life}", True, WHITE)
        screen.blit(life_text, (SCREEN_WIDTH - life_text.get_width() - 10, 10))


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