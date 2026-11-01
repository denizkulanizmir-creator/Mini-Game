import pygame
import json
import os
import sys

TILE = 32
COLS, ROWS = 20, 15
WIDTH, HEIGHT = COLS * TILE, ROWS * TILE


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE = get_base_path()
EXE_DIR = get_exe_dir()
ASSETS = os.path.join(BASE, "assets")
TILES_DIR = os.path.join(ASSETS, "tiles")
BGS_DIR = os.path.join(ASSETS, "backgrounds")
SPRITES_DIR = os.path.join(ASSETS, "sprites")
MAP_FILE = os.path.join(EXE_DIR, "map.json")


def list_png(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))


def load_image(path, size=None):
    if not os.path.exists(path):
        return None
    img = pygame.image.load(path).convert_alpha()
    if size:
        img = pygame.transform.scale(img, size)
    return img


def load_tiles():
    tiles = {}
    for name in list_png(TILES_DIR):
        img = load_image(os.path.join(TILES_DIR, name), (TILE, TILE))
        if img:
            tiles[name] = img
    return tiles


def load_backgrounds():
    bgs = {}
    for name in list_png(BGS_DIR):
        img = load_image(os.path.join(BGS_DIR, name), (WIDTH, HEIGHT))
        if img:
            bgs[name] = img
    return bgs


def load_player():
    for name in list_png(SPRITES_DIR):
        img = load_image(os.path.join(SPRITES_DIR, name), (TILE, TILE))
        if img:
            return img
    return None


def empty_map():
    return {"background": None, "tiles": [], "playerStart": {"x": 1, "y": 1}}


def save_map(data):
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_map():
    if not os.path.exists(MAP_FILE):
        return empty_map()
    try:
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return empty_map()


def draw_tiles(screen, tiles, data):
    for t in data["tiles"]:
        name = t["name"]
        if name in tiles:
            screen.blit(tiles[name], (t["x"] * TILE, t["y"] * TILE))


def editor_loop(screen, tiles, bgs):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)

    data = load_map()
    tile_names = list(tiles.keys())
    bg_names = list(bgs.keys())
    selected_tile = tile_names[0] if tile_names else None
    selected_bg = data.get("background")

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_s:
                    save_map(data)
                    print("[OK] Map saved:", MAP_FILE)
                if event.key == pygame.K_l:
                    data = load_map()
                    selected_bg = data.get("background")
                if event.key == pygame.K_r:
                    running = False
                if event.key == pygame.K_c:
                    data["tiles"] = []
                    data["background"] = None
                    selected_bg = None
                if event.key == pygame.K_TAB and tile_names:
                    idx = tile_names.index(selected_tile) if selected_tile in tile_names else -1
                    selected_tile = tile_names[(idx + 1) % len(tile_names)]
                if event.key == pygame.K_b and bg_names:
                    idx = bg_names.index(selected_bg) if selected_bg in bg_names else -1
                    selected_bg = bg_names[(idx + 1) % len(bg_names)]
                    data["background"] = selected_bg

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                cx, cy = mx // TILE, my // TILE
                if not (0 <= cx < COLS and 0 <= cy < ROWS):
                    continue

                if event.button == 1:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        data["playerStart"] = {"x": cx, "y": cy}
                    elif selected_tile:
                        data["tiles"] = [
                            t for t in data["tiles"]
                            if not (t["x"] == cx and t["y"] == cy)
                        ]
                        data["tiles"].append(
                            {"name": selected_tile, "x": cx, "y": cy}
                        )
                elif event.button == 3:
                    data["tiles"] = [
                        t for t in data["tiles"]
                        if not (t["x"] == cx and t["y"] == cy)
                    ]

        screen.fill((20, 20, 20))
        if selected_bg and selected_bg in bgs:
            screen.blit(bgs[selected_bg], (0, 0))

        for y in range(ROWS):
            for x in range(COLS):
                pygame.draw.rect(
                    screen, (40, 40, 40),
                    (x * TILE, y * TILE, TILE, TILE), 1
                )

        draw_tiles(screen, tiles, data)

        ps = data["playerStart"]
        pygame.draw.rect(
            screen, (0, 255, 0),
            (ps["x"] * TILE, ps["y"] * TILE, TILE, TILE), 2
        )
        screen.blit(
            font.render("P", True, (0, 255, 0)),
            (ps["x"] * TILE + 12, ps["y"] * TILE + 8)
        )

        info = [
            f"EDITOR  |  Tile: {selected_tile or '-'}  (TAB)  |  BG: {selected_bg or '-'}  (B)",
            "Left click: place  |  Right click: delete  |  Shift+Left: player start",
            "S: save  |  L: load  |  C: clear  |  R: play  |  ESC: quit",
        ]
        for i, line in enumerate(info):
            screen.blit(
                font.render(line, True, (200, 200, 200)),
                (10, HEIGHT - 60 + i * 18)
            )

        pygame.display.flip()
        clock.tick(60)

    return data


def game_loop(screen, tiles, bgs, player_img, data):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    player = dict(data["playerStart"])
    blocked = {(t["x"], t["y"]) for t in data["tiles"]}
    bg = bgs.get(data.get("background"))

    running = True
    move_delay = 120
    last_move = 0

    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        if now - last_move > move_delay:
            nx, ny = player["x"], player["y"]
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                ny -= 1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                ny += 1
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                nx -= 1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                nx += 1

            if (nx, ny) != (player["x"], player["y"]):
                if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in blocked:
                    player["x"], player["y"] = nx, ny
                last_move = now

        screen.fill((0, 0, 0))
        if bg:
            screen.blit(bg, (0, 0))

        draw_tiles(screen, tiles, data)

        px, py = player["x"] * TILE, player["y"] * TILE
        if player_img:
            screen.blit(player_img, (px, py))
        else:
            pygame.draw.rect(
                screen, (255, 255, 0),
                (px + 4, py + 4, TILE - 8, TILE - 8)
            )

        screen.blit(
            font.render(
                "GAME  |  Arrows/WASD: move  |  ESC: back to editor",
                True, (200, 200, 200)
            ),
            (10, HEIGHT - 28)
        )

        pygame.display.flip()
        clock.tick(60)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + 80))
    pygame.display.set_caption("Mini Game - Editor + Game")

    tiles = load_tiles()
    bgs = load_backgrounds()
    player_img = load_player()

    if not tiles:
        print("[WARN] assets/tiles/ is empty. Add PNG files first.")
    if not bgs:
        print("[WARN] assets/backgrounds/ is empty.")
    if not player_img:
        print("[WARN] assets/sprites/ is empty. Player will be drawn as a yellow square.")

    while True:
        data = editor_loop(screen, tiles, bgs)
        game_loop(screen, tiles, bgs, player_img, data)


if __name__ == "__main__":
    main()