import pygame
import random
import sys
import os
import asyncio

# Global constants for game settings, colors, and asset loading functions. We define the game window size, 
# player and guard speeds, sizes of sprites, the value needed to open the exit, time limit, starting lives, 
# and invincibility time after being caught.
WIDTH = 900
HEIGHT = 600
FPS = 60

PLAYER_SPEED = 4
GUARD_SPEED = 2

PLAYER_SIZE = 40
GUARD_SIZE = 40
ITEM_SIZE = 34

NEEDED_VALUE = 250 #threshold to open the exit door
TIME_LIMIT = 90
START_LIVES = 3
INVINCIBLE_TIME = 1.2

# Assets are in an "assets" folder next to this script so that we can load them with a relative path, 
# and it works even if the current working directory is different.
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Image load function
def load_img(name, size):
    path = os.path.join(ASSET_DIR, name)
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    except Exception:
        return None

# Sound load function
def load_snd(name):
    path = os.path.join(ASSET_DIR, name)
    try:                                 # Sound loading can fail if no audio device is available, so we catch exceptions and return None in that case.
        return pygame.mixer.Sound(path)
    except Exception:
        return None

# Simple movement function that moves a rect and handles collisions with walls by pushing the rect out of the wall.
def move_with_walls(rect, move_x, move_y, walls):
    # Move on X first, fix overlap, then Y (simple collision handling)
    rect.x += move_x
    for wall in walls:
        if rect.colliderect(wall):
            if move_x > 0:
                rect.right = wall.left
            elif move_x < 0:
                rect.left = wall.right

    rect.y += move_y
    for wall in walls:
        if rect.colliderect(wall):
            if move_y > 0:
                rect.bottom = wall.top
            elif move_y < 0:
                rect.top = wall.bottom


def museum_walls():
    walls = []

    # outer border
    walls.append(pygame.Rect(0, 0, WIDTH, 18))
    walls.append(pygame.Rect(0, HEIGHT - 18, WIDTH, 18))
    walls.append(pygame.Rect(0, 0, 18, HEIGHT))
    walls.append(pygame.Rect(WIDTH - 18, 0, 18, HEIGHT))

    # inside walls
    walls.append(pygame.Rect(150, 80, 18, 440))
    walls.append(pygame.Rect(150, 80, 260, 18))
    walls.append(pygame.Rect(410, 80, 18, 188))
    walls.append(pygame.Rect(260, 250, 168, 18))

    walls.append(pygame.Rect(520, 90, 18, 430))
    walls.append(pygame.Rect(520, 90, 260, 18))
    walls.append(pygame.Rect(780, 90, 18, 248))
    walls.append(pygame.Rect(690, 320, 108, 18))

    walls.append(pygame.Rect(290, 370, 230, 18))
    walls.append(pygame.Rect(600, 480, 160, 18))
    return walls

# Spawn item function that tries to place items in random locations that don't collide with walls or other items, and gives them a type and value.
def spawn_items(walls, count=8):
    types = [("painting.png", 50), ("gem.png", 80), ("statue.png", 120)] # list of item types with their corresponding image names and values for scoring
    items = []
    tries = 0
    while len(items) < count and tries < 2000:
        tries += 1
        img_name, item_value = random.choice(types)
        item_rect = pygame.Rect(
            random.randint(40, WIDTH - 40 - ITEM_SIZE),
            random.randint(40, HEIGHT - 40 - ITEM_SIZE),
            ITEM_SIZE,
            ITEM_SIZE,
        )
        # We check if the item collides with any walls (with a small buffer) 
        # or existing items (with a slightly larger buffer to make sure they don't spawn too close to each other), 
        # and if it does, we discard it and try again. Otherwise, we add it to the list of items with its rect, 
        # image name, value, and a "got" flag to track if the player has collected it.
        ok = True
        for wall in walls:
            if item_rect.colliderect(wall.inflate(10, 10)):
                ok = False
                break
        if not ok:
            continue
        for existing in items:
            if item_rect.colliderect(existing["rect"].inflate(15, 15)):
                ok = False
                break
        if not ok:
            continue
        items.append({"rect": item_rect, "img": img_name, "value": item_value, "got": False}) #append as a dict to store more info about the item
    return items

# Function to create a cone-shaped surface for guard vision, with transparency. We also create a mask from this surface for pixel-perfect collision detection.
def make_cone_surface(length=170, width=150):
    surf = pygame.Surface((length, width), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    pts = [(0, width // 2), (length, 0), (length, width)]
    pygame.draw.polygon(surf, (255, 60, 60, 70), pts)
    pygame.draw.polygon(surf, (255, 60, 60, 140), pts, 2)
    return surf, pygame.mask.from_surface(surf)

# Function to get the facing angle of a guard based on its facing direction, which we use to rotate the vision cone.
def facing_angle(face):
    if face == "RIGHT":
        return 0
    if face == "DOWN":
        return 90
    if face == "LEFT":
        return 180
    return 270 


def play(sound):
    try:
        if sound:
            sound.play()
    except Exception:
        pass

# Function to start a new game by initializing the player's position, exit position, spawning items, 
# setting score, lives, timers, and guard positions and patrol routes in a dictionary.
def new_game(walls):
    game = {}
    game["player"] = pygame.Rect(60, HEIGHT - 90, PLAYER_SIZE, PLAYER_SIZE)
    game["exit"] = pygame.Rect(WIDTH - 86, 40, 56, 56)
    game["items"] = spawn_items(walls, 8)
    game["value"] = 0
    game["lives"] = START_LIVES
    game["inv"] = 0.0
    game["blink"] = 0.0
    game["time"] = float(TIME_LIMIT)

    game["guards"] = [
        {"rect": pygame.Rect(250, 120, GUARD_SIZE, GUARD_SIZE), "mode": "H", "dir": 1, "min": 170, "max": 380, "face": "RIGHT"},
        {"rect": pygame.Rect(640, 140, GUARD_SIZE, GUARD_SIZE), "mode": "V", "dir": 1, "min": 120, "max": 420, "face": "DOWN"},
        {"rect": pygame.Rect(360, 470, GUARD_SIZE, GUARD_SIZE), "mode": "H", "dir": -1, "min": 220, "max": 480, "face": "LEFT"},
    ]
    return game


async def main():
    # Initialize Pygame, create the window, load assets, and set up the game state.
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Museum Heist")
    clock = pygame.time.Clock()

    try:
        pygame.mixer.init()
    except Exception:
        pass

    font = pygame.font.Font(None, 34)
    big = pygame.font.Font(None, 90)
    title = pygame.font.Font(None, 110)

    icon = load_img("icon.png", (64, 64))
    if icon:
        pygame.display.set_icon(icon)

    floor = load_img("floor.jfif", (96, 96))
    menu_bg = pygame.transform.smoothscale(floor, (WIDTH, HEIGHT)) if floor else None
    menu_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    menu_overlay.fill((0, 0, 0, 130))  # makes text readable

    player_img = load_img("player.png", (PLAYER_SIZE, PLAYER_SIZE))
    guard_img = load_img("guard.png", (GUARD_SIZE, GUARD_SIZE))
    exit_img = load_img("exit.png", (56, 56))

    items_img = {
        "painting.png": load_img("painting.png", (ITEM_SIZE, ITEM_SIZE)),
        "gem.png": load_img("gem.png", (ITEM_SIZE, ITEM_SIZE)),
        "statue.png": load_img("statue.png", (ITEM_SIZE, ITEM_SIZE)),
    }

    collect_s = load_snd("collect.ogg")
    caught_s = load_snd("caught.ogg")
    win_s = load_snd("win.ogg")
    startup_s = load_snd("startup.ogg")
    gameover_s = load_snd("gameover.ogg")

    walls = museum_walls()
    game = new_game(walls)

    cone_base, cone_base_mask = make_cone_surface()
    # Surface for the flashlight effect, starts fully transparent and we draw a transparent circle around the player to create a light radius.
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA) 

    state = "START"
    player_move_x = 0
    player_move_y = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        await asyncio.sleep(0)
        if dt > 0.05: # cap delta time to avoid big jumps if the game lags or is paused in a debugger, which can cause issues with movement and timers.
            dt = 0.05

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state in ("START", "WIN", "GAME_OVER") and event.type == pygame.KEYDOWN:
                if state == "START" and event.key == pygame.K_SPACE:
                    play(startup_s)
                    state = "PLAYING"
                if state in ("WIN", "GAME_OVER") and event.key == pygame.K_r:
                    play(startup_s)
                    game = new_game(walls)
                    player_move_x = 0
                    player_move_y = 0
                    state = "PLAYING"
            # Movement Input Handling
            if state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        player_move_x = -PLAYER_SPEED
                    if event.key == pygame.K_RIGHT:
                        player_move_x = PLAYER_SPEED
                    if event.key == pygame.K_UP:
                        player_move_y = -PLAYER_SPEED
                    if event.key == pygame.K_DOWN:
                        player_move_y = PLAYER_SPEED
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        player_move_x = 0
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        player_move_y = 0

        if state == "START":
            screen.blit(menu_bg, (0, 0))
            screen.blit(menu_overlay, (0, 0))
            screen.blit(title.render("MUSEUM HEIST", True, (240, 235, 210)), (WIDTH // 2 - 270, 120))
            screen.blit(font.render("Arrow keys to move", True, (210, 210, 230)), (WIDTH // 2 - 120, 320))
            screen.blit(font.render("Avoid guards and collect items", True, (210, 210, 230)), (WIDTH // 2 - 170, 370))
            screen.blit(font.render(f"Collect at least {NEEDED_VALUE} value to open the exit", True, (210, 210, 230)), (WIDTH // 2 - 220, 420))
            screen.blit(font.render("Press SPACE to start", True, (255, 230, 120)), (WIDTH // 2 - 130, 500))
            pygame.display.update()
            continue

        if state == "WIN":
            screen.blit(menu_bg, (0, 0))
            screen.blit(menu_overlay, (0, 0))
            screen.blit(big.render("ESCAPED!", True, (80, 240, 160)), (WIDTH // 2 - 180, 170))
            screen.blit(font.render(f"Final Value: {game['value']}", True, (230, 230, 240)), (WIDTH // 2 - 110, 290))
            screen.blit(font.render("Press R to play again", True, (255, 230, 120)), (WIDTH // 2 - 150, 380))
            pygame.display.update()
            continue

        if state == "GAME_OVER":
            screen.blit(menu_bg, (0, 0))
            screen.blit(menu_overlay, (0, 0))
            screen.blit(big.render("CAUGHT!", True, (240, 70, 70)), (WIDTH // 2 - 150, 170))
            screen.blit(font.render(f"Final Value: {game['value']}", True, (230, 230, 240)), (WIDTH // 2 - 110, 290))
            screen.blit(font.render("Press R to replay", True, (255, 230, 120)), (WIDTH // 2 - 110, 380))
            pygame.display.update()
            continue

        # PLAYING
        # Update timers and if time runs out, go to game over state. 
        game["time"] -= dt
        if game["time"] <= 0:
            state = "GAME_OVER"
            play(gameover_s)
        # Handle invincibility timer and blinking effect after being caught. 
        if game["inv"] > 0:
            game["inv"] -= dt
            game["blink"] += dt
        else:
            game["blink"] = 0.0

        move_with_walls(game["player"], player_move_x, player_move_y, walls)

        for it in game["items"]:
            if it["got"]:
                continue
            if game["player"].colliderect(it["rect"]):
                it["got"] = True
                game["value"] += it["value"]
                play(collect_s)

        touching_guard = False
        for guard in game["guards"]:
            if guard["mode"] == "H":
                guard["rect"].x += GUARD_SPEED * guard["dir"]
                if guard["rect"].x < guard["min"]:
                    guard["rect"].x = guard["min"]
                    guard["dir"] *= -1
                if guard["rect"].x > guard["max"]:
                    guard["rect"].x = guard["max"]
                    guard["dir"] *= -1
                guard["face"] = "RIGHT" if guard["dir"] > 0 else "LEFT"
            else:
                guard["rect"].y += GUARD_SPEED * guard["dir"]
                if guard["rect"].y < guard["min"]:
                    guard["rect"].y = guard["min"]
                    guard["dir"] *= -1
                if guard["rect"].y > guard["max"]:
                    guard["rect"].y = guard["max"]
                    guard["dir"] *= -1
                guard["face"] = "DOWN" if guard["dir"] > 0 else "UP"

            if game["player"].colliderect(guard["rect"]):
                touching_guard = True

        open_exit = game["value"] >= NEEDED_VALUE
        if open_exit and game["player"].colliderect(game["exit"]):
            play(win_s)
            state = "WIN"

        # draw floor like a grid of tiles
        for y in range(0, HEIGHT, 96):
            for x in range(0, WIDTH, 96):
                screen.blit(floor, (x, y))


        # draw walls + exit + items
        for wall in walls:
            pygame.draw.rect(screen, (22, 22, 28), wall)
            pygame.draw.rect(screen, (70, 70, 80), wall, 2)


        screen.blit(exit_img, game["exit"].topleft)
        
        # If the exit is open, draw a bright border around it, otherwise draw a red border and a "LOCKED" label.
        if open_exit:
            pygame.draw.rect(screen, (80, 240, 160), game["exit"], 3, border_radius=10)
        else:
            pygame.draw.rect(screen, (240, 90, 90), game["exit"], 3, border_radius=10)
            screen.blit(font.render("LOCKED", True, (240, 90, 90)), (game["exit"].x - 10, game["exit"].y + 62))

        for it in game["items"]:
            if it["got"]:
                continue
            img = items_img.get(it["img"])
            screen.blit(img, it["rect"].topleft)
            

        # guards + cones + vision collision
        player_mask = pygame.mask.from_surface(player_img) if player_img else None
        seen = False
        # We draw the guards and their vision cones, and check if the player is within the cone using pixel-perfect collision detection with masks.  
        for guard in game["guards"]:
            screen.blit(guard_img, guard["rect"].topleft)
            ang = facing_angle(guard["face"])
            cone = pygame.transform.rotate(cone_base, -ang)
            cone_mask = pygame.mask.from_surface(cone)
            cone_rect = cone.get_rect(center=guard["rect"].center)

            if guard["face"] == "RIGHT":
                cone_rect.left = guard["rect"].centerx
            elif guard["face"] == "LEFT":
                cone_rect.right = guard["rect"].centerx
            elif guard["face"] == "DOWN":
                cone_rect.top = guard["rect"].centery
            else:
                cone_rect.bottom = guard["rect"].centery

            screen.blit(cone, cone_rect.topleft)

            if game["inv"] <= 0 and player_mask:
                off = (game["player"].x - cone_rect.x, game["player"].y - cone_rect.y)
                if cone_mask.overlap(player_mask, off) is not None:
                    seen = True
        # If the player is seen by a guard or touching a guard, and they are not currently invincible from a recent hit, they lose a life 
        # and get reset to the starting position with temporary invincibility. If they run out of lives, it's game over.
        if (seen or touching_guard) and game["inv"] <= 0:
            game["lives"] -= 1
            play(caught_s)
            if game["lives"] <= 0:
                state = "GAME_OVER"
                play(gameover_s)
            else:
                game["player"].x = 60
                game["player"].y = HEIGHT - 90
                game["inv"] = INVINCIBLE_TIME
                game["blink"] = 0.0
                player_move_x = 0
                player_move_y = 0

        # player (blink after hit)
        show = True
        if game["inv"] > 0 and int(game["blink"] * 10) % 2 == 0:
            show = False
        if show:
            screen.blit(player_img, game["player"].topleft)
        
        # HUD 
        screen.blit(font.render(f"Value: {game['value']} / {NEEDED_VALUE}", True, WHITE), (18, 18))
        screen.blit(font.render(f"Lives: {game['lives']}", True, WHITE), (18, 52))
        screen.blit(font.render(f"Time: {max(0, int(game['time']))}", True, WHITE), (18, 86))

        # simple flashlight 
        darkness.fill((0, 0, 0, 210))
        pygame.draw.circle(darkness, (0, 0, 0, 0), game["player"].center, 140)
        screen.blit(darkness, (0, 0))

        # If the exit is open, show a hint about it, otherwise show a hint about needing more value to open it.
        if open_exit:
            hint = font.render("Exit is OPEN!", True, (80, 240, 160))
        else:
            hint = font.render("Collect more value to open the exit.", True, (255, 230, 120))
        screen.blit(hint, (WIDTH - hint.get_width() - 16, 18))

        pygame.display.update()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())

