"""
Sporty Saab - Projectile Motion Volleyball Game (tkinter)
----------------------------------------------------------
Pick a mode first:

  SINGLE PLAYER  You are the thrower and control the trajectory live (same
                 controls as Player 1 below). An AI controls the volleyball
                 player and tries to catch the balls.

  MULTIPLAYER    Player 1 = THROWER: controls the trajectory (live!) and
                            decides when to throw a volleyball or a basketball.
                 Player 2 = CATCHER: controls the volleyball player.

Three levels, each one a different projectile-motion case:
  Level 1 - Horizontal launch          (height, gravity, velocity)
  Level 2 - Launch at an angle         (velocity, gravity, angle)
  Level 3 - Launch at an angle from a height
                                       (velocity, angle, gravity, height)

Controls
  Player 1 / you (thrower)   W / S   height: higher / lower
                       A / D   distance: A = nearer, D = farther
                       Q / E   starting height down / up   (level 3)
                       F       throw a VOLLEYBALL
                       G       throw a BASKETBALL
  Player 2 (catcher)   Arrow keys   move
                       SPACE        open / close hands

Scoring (both modes; in single player the AI is the catcher)
  Catcher : volleyball caught +10, basketball caught -10
  Thrower : +10 when the catcher grabs a basketball
            +10 when a volleyball hits the floor

After each level the program shows Range, Maximum height, Time of flight
and the Trajectory equation, calculated from the physics formulas.
"""

import math
import random
import time
import tkinter as tk
import tkinter.font as tkfont


# ----------------------------------------------------------------- constants
W, H_CANVAS = 1000, 620
FLOOR_TOP = 495            # where the gym floor begins
GROUND_Y = 540             # y pixel where athletes stand / balls land
X0 = 140                   # x pixel of the launch point
PLOT_W = 740               # horizontal pixels available for the trajectory
PLOT_H = GROUND_Y - 100    # vertical pixels available for the trajectory
MULTI_THROWS = 10          # throws per level
THROW_COOLDOWN = 0.7       # seconds between throws
LEVEL_TIME = 90            # seconds per level
BALL_R = 14
CATCH_R = 38
PLAYER_SPEED = 450         # px / s for the human catcher
# ---- AI difficulty (make the AI smarter by raising speed / chances, lowering the rest)
AI_SPEED = 250             # px / s the AI can move (human catcher: 450)
AI_REACT = (0.35, 0.9)     # seconds before the AI notices a new ball (min, max)
AI_PLAN_LAG = 0.3          # extra seconds the AI needs to commit to an intercept point
AI_SEES_V = 0.65           # chance the AI goes for a given volleyball
AI_SEES_B = 0.25           # chance the AI wrongly goes for a given basketball
AI_ERR = 22                # aim error in pixels (std-dev); catch radius is 38
BLUE = "#1e63d6"
PANEL = "#164aa3"
SKIN = "#f1c27d"
ARROWS = ("Left", "Right", "Up", "Down")


# fields: (label, key, default)
LEVELS = [
    {
        "name": "Horizontal Launch",
        "fields": [
            ("Initial height  h  (m)", "h", "20"),
            ("Gravity  g  (m/s²)", "g", "9.8"),
            ("Initial velocity  vₓ  (m/s)", "v", "12"),
        ],
    },
    {
        "name": "Launch at an Angle",
        "fields": [
            ("Initial velocity  v₀  (m/s)", "v", "20"),
            ("Gravity  g  (m/s²)", "g", "9.8"),
            ("Launch angle  θ  (degrees)", "a", "45"),
        ],
    },
    {
        "name": "Launch at an Angle from a Height",
        "fields": [
            ("Initial velocity  v₀  (m/s)", "v", "15"),
            ("Launch angle  θ  (degrees)", "a", "30"),
            ("Gravity  g  (m/s²)", "g", "9.8"),
            ("Initial height  h  (m)", "h", "10"),
        ],
    },
]


# ------------------------------------------------------------------- physics
def compute(level, p):
    """Apply the projectile-motion formulas for the given level.

    Returns a dict with R, H, T, the launch components used by the animation,
    and text lines describing each formula with the numbers substituted in.
    """
    g, v = p["g"], p["v"]

    if level == 0:                                   # ---- horizontal launch
        h = p["h"]
        T = math.sqrt(2 * h / g)                     # T = sqrt(2h/g)
        R = v * T                                    # R = vx * sqrt(2h/g)
        Hm = h                                       # H = h
        vx, vy, y0 = v, 0.0, h
        a = g / (2 * v * v)
        lines = [
            ("Range", f"R = vₓ·√(2h/g) = {v:.4g}·√(2·{h:.4g}/{g:.4g})", R, "m"),
            ("Maximum height", f"H = h = {h:.4g}", Hm, "m"),
            ("Time of flight", f"T = √(2h/g) = √(2·{h:.4g}/{g:.4g})", T, "s"),
        ]
        traj = ("y = h − g·x² / (2·vₓ²)",
                f"y = {h:.4g} − {a:.5g}·x²")

    else:
        ang = math.radians(p["a"])
        s, c = math.sin(ang), math.cos(ang)
        vx, vy = v * c, v * s
        if level == 1:                               # ---- angle, from ground
            h = 0.0
            T = 2 * v * s / g                        # T = 2 v0 sinθ / g
            R = v * v * math.sin(2 * ang) / g        # R = v0² sin2θ / g
            Hm = v * v * s * s / (2 * g)             # H = v0² sin²θ / 2g
            y0 = 0.0
            lines = [
                ("Range", f"R = v₀² sin(2θ)/g = {v:.4g}²·sin(2·{p['a']:.4g}°)/{g:.4g}", R, "m"),
                ("Maximum height", f"H = v₀² sin²θ/(2g) = {v:.4g}²·sin²({p['a']:.4g}°)/(2·{g:.4g})", Hm, "m"),
                ("Time of flight", f"T = 2v₀ sinθ/g = 2·{v:.4g}·sin({p['a']:.4g}°)/{g:.4g}", T, "s"),
            ]
            gen = "y = x·tanθ − g·x² / (2·v₀²·cos²θ)"
            pre = ""
        else:                                        # ---- angle, from height
            h = p["h"]
            T = (v * s + math.sqrt((v * s) ** 2 + 2 * g * h)) / g
            R = v * c * T                            # R = v0 cosθ · T
            Hm = h + (v * s) ** 2 / (2 * g) if s > 0 else h
            y0 = h
            lines = [
                ("Range", f"R = v₀cosθ·T = {v:.4g}·cos({p['a']:.4g}°)·{T:.4f}", R, "m"),
                ("Maximum height", f"H = h + v₀² sin²θ/(2g) = {h:.4g} + {v:.4g}²·sin²({p['a']:.4g}°)/(2·{g:.4g})"
                 + ("" if s > 0 else "   (thrown downward → peak is the launch height)"), Hm, "m"),
                ("Time of flight",
                 f"T = [v₀sinθ + √((v₀sinθ)² + 2gh)]/g = [{v:.4g}·sin({p['a']:.4g}°) + "
                 f"√(({v:.4g}·sin({p['a']:.4g}°))² + 2·{g:.4g}·{h:.4g})]/{g:.4g}", T, "s"),
            ]
            gen = "y = h + x·tanθ − g·x² / (2·v₀²·cos²θ)"
            pre = f"{h:.4g} + "

        if abs(c) < 1e-9:                            # straight up: no y(x)
            traj = (gen, f"x = 0 (vertical throw):  y = {h:.4g} + {vy:.4g}·t − ½·{g:.4g}·t²")
        else:
            a = g / (2 * v * v * c * c)
            traj = (gen, f"y = {pre}{math.tan(ang):.5g}·x − {a:.5g}·x²")

    return dict(R=R, H=Hm, T=T, vx=vx, vy=vy, y0=y0, g=g, lines=lines, traj=traj)


# ------------------------------------------------------------ small helpers
def pos_at(res, t):
    """(x, y) in metres of a ball with trajectory `res` at time t."""
    return res["vx"] * t, res["y0"] + res["vy"] * t - 0.5 * res["g"] * t * t


def to_px(x, y, scale):
    return X0 + x * scale, GROUND_Y - BALL_R - y * scale


def calc_scale(res):
    """Pixels per metre so the whole trajectory fits on the screen."""
    cands = []
    if res["R"] > 1e-9:
        cands.append(PLOT_W / res["R"])
    if res["H"] > 1e-9:
        cands.append(PLOT_H / res["H"])
    return min(cands) if cands else 10.0


def play_speed(res):
    """Play back at real time when the flight lasts 1.5-6 s, otherwise
    speed up / slow down so every throw is watchable."""
    T = res["T"]
    return T / min(max(T, 1.5), 6.0)


def fmt_params(level, p):
    parts = [f"v = {p['v']:.4g} m/s"]
    if level in (1, 2):
        parts.append(f"θ = {p['a']:.4g}°")
    if level in (0, 2):
        parts.append(f"h = {p['h']:.4g} m")
    parts.append(f"g = {p['g']:.4g} m/s²")
    return "   ".join(parts)


def draw_volleyball(c, x, y, r, tag):
    lw = max(2, round(r / 7))
    c.create_oval(x - r, y - r, x + r, y + r, fill="#fff6c2", outline="#1f4fa3", width=lw, tags=tag)
    c.create_line(x - r * .9, y - r * .35, x, y - r * .1, x + r * .9, y - r * .35,
                  smooth=True, fill="#1f4fa3", width=lw, tags=tag)
    c.create_line(x - r * .9, y + r * .35, x, y + r * .1, x + r * .9, y + r * .35,
                  smooth=True, fill="#1f4fa3", width=lw, tags=tag)
    c.create_line(x, y - r, x - r * .15, y, x, y + r, smooth=True, fill="#d4a017", width=lw, tags=tag)


def draw_basketball(c, x, y, r, tag):
    c.create_oval(x - r, y - r, x + r, y + r, fill="#e8741e", outline="#222", width=2, tags=tag)
    c.create_line(x, y - r, x, y + r, fill="#222", width=2, tags=tag)
    c.create_line(x - r, y, x + r, y, fill="#222", width=2, tags=tag)
    c.create_line(x - r * .7, y - r * .7, x - r * .3, y, x - r * .7, y + r * .7,
                  smooth=True, fill="#222", width=2, tags=tag)
    c.create_line(x + r * .7, y - r * .7, x + r * .3, y, x + r * .7, y + r * .7,
                  smooth=True, fill="#222", width=2, tags=tag)


# ----------------------------------------------------------------------- app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sporty Saab")
        self.geometry(f"{W}x{H_CANVAS}")
        self.resizable(False, False)
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.mode = "single"          # "single" or "multi"
        self.level = 0
        self.total = 0                # single player total
        self.p1_total = 0             # multiplayer totals
        self.p2_total = 0
        self.running = False
        self._job = None
        self.keys = set()
        self.last_space = 0.0
        self.hands_open = False
        self.balls = []
        self.popups = []

        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<FocusOut>", lambda e: self.keys.clear())
        self.show_mode_select()

    @property
    def p1_name(self):
        return "You" if self.mode == "single" else "Player 1"

    @property
    def p2_name(self):
        return "AI" if self.mode == "single" else "Player 2"

    # ----------------------------------------------------------- utilities
    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def blue_frame(self):
        self.clear()
        f = tk.Frame(self.container, bg=BLUE)
        f.pack(fill="both", expand=True)
        return f

    def draw_logo(self, parent, size=54):
        """'Sporty Saab' where the 'o' of Sporty is a volleyball."""
        font = tkfont.Font(family="Helvetica", size=size, weight="bold")
        left, right = "Sp", "rty Saab"
        wl, wr = font.measure(left), font.measure(right)
        d = int(font.measure("o") * 0.95)
        gap = 3
        total = wl + gap + d + gap + wr
        top = 8
        base = top + font.metrics("ascent")
        cv = tk.Canvas(parent, width=W, height=font.metrics("linespace") + 16,
                       bg=BLUE, highlightthickness=0)
        x = (W - total) / 2
        cv.create_text(x, top, text=left, anchor="nw", font=font, fill="white")
        x += wl + gap
        draw_volleyball(cv, x + d / 2, base - d / 2 - 1, d / 2, "logo")
        x += d + gap
        cv.create_text(x, top, text=right, anchor="nw", font=font, fill="white")
        return cv

    # -------------------------------------------------- mode select screen
    def show_mode_select(self):
        self.running = False
        f = self.blue_frame()
        self.draw_logo(f).pack(pady=(45, 0))
        tk.Label(f, text="Projectile Motion Volleyball", bg=BLUE, fg="#cfe0ff",
                 font=("Helvetica", 16)).pack(pady=(0, 18))
        tk.Label(f, text="Choose a game mode", bg=BLUE, fg="white",
                 font=("Helvetica", 22, "bold")).pack(pady=(10, 18))

        row = tk.Frame(f, bg=BLUE)
        row.pack(pady=6)
        options = [
            ("Single Player", "single",
             "You are the thrower.\nYou control the trajectory live and decide what to throw,\n"
             "while an AI volleyball player tries to catch the balls."),
            ("Multiplayer", "multi",
             "Two players, one keyboard.\nPlayer 1 controls the thrower and the trajectory,\n"
             "Player 2 controls the volleyball player."),
        ]
        for col, (label, mode, desc) in enumerate(options):
            card = tk.Frame(row, bg=PANEL, padx=24, pady=20)
            card.grid(row=0, column=col, padx=20)
            tk.Button(card, text=label, font=("Helvetica", 20, "bold"), width=16,
                      command=lambda m=mode: self.choose_mode(m)).pack()
            tk.Label(card, text=desc, bg=PANEL, fg="#cfe0ff", font=("Helvetica", 12),
                     justify="center").pack(pady=(14, 0))

    def choose_mode(self, mode):
        self.mode = mode
        self.show_instructions()

    # ------------------------------------------------- instructions screen
    def show_instructions(self):
        self.running = False
        f = self.blue_frame()
        tk.Label(f, text="Sporty Saab", bg=BLUE, fg="white",
                 font=("Helvetica", 30, "bold")).pack(pady=(50, 4))
        tk.Label(f, text="Single Player" if self.mode == "single" else "Multiplayer",
                 bg=BLUE, fg="#ffe14d", font=("Helvetica", 20, "bold")).pack(pady=(0, 18))

        if self.mode == "single":
            txt = ("YOU – THROWER  (controls the trajectory)\n"
                   "Type your starting values, then fine-tune them live:\n"
                   "W / S = height (up / down)     A / D = distance (A = near, D = far)\n"
                   "Q / E = starting height (level 3)     F = throw volleyball     G = throw basketball\n\n"
                   "AI – CATCHER  (moves and opens its hands by itself)\n\n"
                   "AI:  volleyball caught +10,  basketball caught −10\n"
                   "You:  +10 when a basketball is caught,  +10 when a volleyball hits the floor\n"
                   f"{MULTI_THROWS} throws per level  •  3 levels  •  highest total wins")
        else:
            txt = ("PLAYER 1 – THROWER  (controls the trajectory)\n"
                   "Type your starting values, then fine-tune them live:\n"
                   "W / S = height (up / down)     A / D = distance (A = near, D = far)\n"
                   "Q / E = starting height (level 3)     F = throw volleyball     G = throw basketball\n\n"
                   "PLAYER 2 – CATCHER  (controls the volleyball player)\n"
                   "Arrow keys = move          SPACEBAR = open / close hands\n\n"
                   "Player 2:  volleyball caught +10,  basketball caught −10\n"
                   "Player 1:  +10 when a basketball is caught,  +10 when a volleyball hits the floor\n"
                   f"{MULTI_THROWS} throws per level  •  3 levels  •  highest total wins")
        tk.Label(f, text=txt, bg=BLUE, fg="white", font=("Helvetica", 14),
                 justify="center").pack(pady=10)

        row = tk.Frame(f, bg=BLUE)
        row.pack(pady=22)
        tk.Button(row, text="Start Game", font=("Helvetica", 18, "bold"), width=14,
                  command=self.new_game).pack(side="left", padx=10)
        tk.Button(row, text="Back", font=("Helvetica", 18, "bold"), width=8,
                  command=self.show_mode_select).pack(side="left", padx=10)

    def new_game(self):
        self.level = 0
        self.total = 0
        self.p1_total = 0
        self.p2_total = 0
        self.show_input()

    # -------------------------------------------------------- input screen
    def show_input(self):
        self.running = False
        info = LEVELS[self.level]
        multi = self.mode == "multi"
        f = self.blue_frame()
        tk.Label(f, text=f"Level {self.level + 1}: {info['name']}", bg=BLUE, fg="white",
                 font=("Helvetica", 28, "bold")).pack(pady=(40 if multi else 50, 5))
        if multi:
            sub = ("Player 1 (Thrower): enter your starting values.\n"
                   "You can fine-tune them live during the level with the W/S, A/D, Q/E keys.")
        else:
            sub = ("Enter your starting values (Earth's gravity is 9.8 m/s²).\n"
                   "You can fine-tune them live during the level with the W/S, A/D, Q/E keys.")
        tk.Label(f, text=sub, bg=BLUE, fg="#cfe0ff", font=("Helvetica", 14)).pack(pady=(0, 22))

        form = tk.Frame(f, bg=BLUE)
        form.pack()
        self.entries = {}
        for r, (label, key, default) in enumerate(info["fields"]):
            tk.Label(form, text=label, bg=BLUE, fg="white", font=("Helvetica", 17),
                     anchor="e", width=28).grid(row=r, column=0, padx=10, pady=9)
            e = tk.Entry(form, font=("Helvetica", 17), width=12, justify="center")
            e.insert(0, default)
            e.grid(row=r, column=1, padx=10, pady=9)
            self.entries[key] = e
            e.bind("<Return>", lambda ev: self.try_start())
        first = info["fields"][0][1]
        self.entries[first].focus_set()

        self.err = tk.Label(f, text="", bg=BLUE, fg="#ffe14d", font=("Helvetica", 14, "bold"),
                            wraplength=800)
        self.err.pack(pady=12)
        tk.Button(f, text="Start Level", font=("Helvetica", 18, "bold"), width=14,
                  command=self.try_start).pack(pady=5)
        score = f"{self.p1_name} (Thrower): {self.p1_total}      {self.p2_name} (Catcher): {self.p2_total}"
        tk.Label(f, text=score, bg=BLUE, fg="white", font=("Helvetica", 14)).pack(pady=18)

    def try_start(self):
        try:
            p = self.parse()
            res = compute(self.level, p)
            if not all(math.isfinite(res[k]) for k in ("R", "H", "T")):
                raise OverflowError
            if res["T"] <= 1e-9:
                raise ValueError("With these values the ball never leaves the ground "
                                 "(time of flight is 0). Try a different set of values.")
        except ValueError as ex:
            self.err.config(text=str(ex))
            return
        except OverflowError:
            self.err.config(text="Those numbers are too extreme to calculate. Try smaller values.")
            return
        self.start_level(p, res)

    def parse(self):
        vals = {}
        for label, key, _ in LEVELS[self.level]["fields"]:
            txt = self.entries[key].get().strip()
            try:
                x = float(txt)
            except ValueError:
                raise ValueError(f"'{label.strip()}' must be a number.")
            if not math.isfinite(x):
                raise ValueError(f"'{label.strip()}' must be a finite number.")
            vals[key] = x
        if vals["g"] <= 0:
            raise ValueError("Gravity must be greater than 0 for the ball to fall.")
        if vals["v"] <= 0:
            raise ValueError("Initial velocity must be greater than 0.")
        if self.level == 0 and vals["h"] <= 0:
            raise ValueError("Initial height must be greater than 0 for a horizontal launch.")
        if self.level == 1 and not (0 < vals["a"] <= 90):
            raise ValueError("For a launch from the ground the angle must be between 0 and 90 degrees.")
        if self.level == 2:
            if vals["h"] < 0:
                raise ValueError("Initial height cannot be negative.")
            if not (-90 <= vals["a"] <= 90):
                raise ValueError("Launch angle must be between -90 and 90 degrees.")
        return vals

    # ------------------------------------------------------------ the game
    def start_level(self, p, res):
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.clear()
        self.p, self.res = dict(p), res
        self.scale = calc_scale(res)
        self.report_res, self.report_p = res, dict(p)

        self.canvas = tk.Canvas(self.container, width=W, height=H_CANVAS, highlightthickness=0)
        self.canvas.pack()
        self.draw_background()

        self.balls = []
        self.popups = []
        self.level_score = 0       # catcher (AI or Player 2)
        self.p1_level = 0          # thrower (you / Player 1)
        self.caught_v = 0
        self.caught_b = 0

        now = time.perf_counter()
        self.throws_left = MULTI_THROWS
        self.last_throw = 0.0
        self.level_end = now + LEVEL_TIME
        self.cx = W - 160
        self.chy = GROUND_Y - 80
        self.idle = (self.cx, self.chy)
        self.hands_open = False
        self.keys.clear()

        self.last = now
        self.running = True
        self.finishing = False
        self.focus_set()
        self.tick()

    # ---- drawing helpers
    def draw_background(self):
        c = self.canvas
        # wall + bleachers
        c.create_rectangle(0, 0, W, FLOOR_TOP, fill="#cfd9e6", outline="", tags="bg")
        for i in range(4):
            c.create_rectangle(0, 60 + i * 26, W, 80 + i * 26, fill="#9fb0c6", outline="", tags="bg")
        c.create_rectangle(0, 0, W, 40, fill="#233a5e", outline="", tags="bg")
        c.create_text(W // 2, 20, text="SPORTY SAAB  –  VOLLEYBALL ARENA", fill="white",
                      font=("Helvetica", 16, "bold"), tags="bg")
        # floor
        c.create_rectangle(0, FLOOR_TOP, W, H_CANVAS, fill="#2f78b7", outline="", tags="bg")
        c.create_polygon(110, FLOOR_TOP + 6, 890, FLOOR_TOP + 6, 975, H_CANVAS - 8, 25, H_CANVAS - 8,
                         fill="#f0a24a", outline="white", width=4, tags="bg")
        # court lines
        c.create_line(110 + 0.13 * 780 * 0.35, FLOOR_TOP + 50, 890 - 0.13 * 780 * 0.35, FLOOR_TOP + 50,
                      fill="white", width=3, tags="bg")
        c.create_line(60, H_CANVAS - 48, 940, H_CANVAS - 48, fill="white", width=3, tags="bg")
        c.create_line(W // 2, FLOOR_TOP + 6, W // 2, H_CANVAS - 8, fill="white", width=3, tags="bg")
        # net
        top, bot = FLOOR_TOP - 105, FLOOR_TOP + 6
        c.create_rectangle(122, top, 878, bot, fill="", outline="#444", width=1, tags="bg")
        for x in range(122, 880, 16):
            c.create_line(x, top, x, bot, fill="#555", tags="bg")
        for y in range(top, bot, 14):
            c.create_line(122, y, 878, y, fill="#555", tags="bg")
        c.create_rectangle(122, top - 3, 878, top + 5, fill="white", outline="#444", tags="bg")
        c.create_rectangle(116, top - 6, 124, bot, fill="#222", outline="", tags="bg")
        c.create_rectangle(876, top - 6, 884, bot, fill="#222", outline="", tags="bg")
        # ground reference line
        c.create_line(0, GROUND_Y, W, GROUND_Y, fill="#ffffff", dash=(2, 6), tags="bg")

    def draw_guide(self):
        """Dashed preview of the current trajectory (updates live in multiplayer)."""
        c = self.canvas
        T = self.res["T"]
        pts = []
        for i in range(61):
            x, y = pos_at(self.res, T * i / 60)
            px, py = to_px(x, max(y, 0), self.scale)
            pts += [px, py]
        c.create_line(*pts, fill="#ffffff", dash=(6, 5), width=2, tags="dyn")
        c.create_oval(pts[-2] - 7, pts[-1] - 7, pts[-2] + 7, pts[-1] + 7,
                      outline="#ffe14d", width=2, tags="dyn")

    def draw_thrower(self):
        c = self.canvas
        lx, ly = to_px(0, self.res["y0"], self.scale)
        bx = lx - 32
        fy = min(ly + 55, GROUND_Y)
        if fy < GROUND_Y:                       # standing on a platform
            c.create_rectangle(bx - 30, fy, bx + 30, GROUND_Y, fill="#7b7f86",
                               outline="#4b4f55", width=2, tags="dyn")
        c.create_line(bx - 7, fy - 56, bx - 7, fy, fill="#222", width=6, tags="dyn")
        c.create_line(bx + 7, fy - 56, bx + 7, fy, fill="#222", width=6, tags="dyn")
        c.create_rectangle(bx - 15, fy - 106, bx + 15, fy - 54, fill="#d62828", outline="#7a1010", tags="dyn")
        c.create_text(bx, fy - 80, text="1", fill="white", font=("Helvetica", 14, "bold"), tags="dyn")
        c.create_line(bx - 10, fy - 98, bx - 22, fy - 68, fill=SKIN, width=6, tags="dyn")
        c.create_line(bx + 10, fy - 98, lx, ly, fill=SKIN, width=6, tags="dyn")
        c.create_oval(lx - 7, ly - 7, lx + 7, ly + 7, fill=SKIN, outline="", tags="dyn")
        c.create_oval(bx - 12, fy - 132, bx + 12, fy - 108, fill=SKIN, outline="#a0763a", tags="dyn")
        label = "P1 THROWER" if self.mode == "multi" else "YOU"
        c.create_text(bx, max(fy - 148, 50), text=label, fill="#222",
                      font=("Helvetica", 10, "bold"), tags="dyn")

    def draw_ball(self, x, y, kind):
        if kind == "V":
            draw_volleyball(self.canvas, x, y, BALL_R, "dyn")
        else:
            draw_basketball(self.canvas, x, y, BALL_R, "dyn")

    def draw_catcher(self):
        c, cx, hy = self.canvas, self.cx, self.chy
        f = min(1.0, (GROUND_Y - hy) / 150)      # body crouches when low
        sh, hip, ft = hy + 50 * f, hy + 100 * f, hy + 150 * f
        head = hy + 26 * f
        c.create_line(cx - 8, hip, cx - 8, ft, fill="#222", width=7, tags="dyn")
        c.create_line(cx + 8, hip, cx + 8, ft, fill="#222", width=7, tags="dyn")
        c.create_rectangle(cx - 16, sh, cx + 16, hip + 2, fill="#ffd60a", outline="#8a7400", tags="dyn")
        c.create_text(cx, (sh + hip) / 2, text="7", fill="#0b3d91", font=("Helvetica", 14, "bold"), tags="dyn")
        for sgn in (-1, 1):
            hx = cx + sgn * 24
            c.create_line(cx + sgn * 12, sh + 4, hx, hy, fill=SKIN, width=6, tags="dyn")
            if self.hands_open:
                c.create_oval(hx - 11, hy - 11, hx + 11, hy + 11, fill=SKIN, outline="#a0763a", width=2, tags="dyn")
                for k in range(-2, 3):
                    ang = math.radians(-90 + k * 25)
                    c.create_line(hx + 9 * math.cos(ang), hy + 9 * math.sin(ang),
                                  hx + 17 * math.cos(ang), hy + 17 * math.sin(ang),
                                  fill=SKIN, width=3, tags="dyn")
            else:
                c.create_oval(hx - 7, hy - 7, hx + 7, hy + 7, fill="#d9a35f", outline="#a0763a", width=2, tags="dyn")
        c.create_oval(cx - 12, head - 12, cx + 12, head + 12, fill=SKIN, outline="#a0763a", tags="dyn")
        label = "P2 CATCHER" if self.mode == "multi" else "AI CATCHER"
        c.create_text(cx, max(head - 26, 50), text=label, fill="#222",
                      font=("Helvetica", 10, "bold"), tags="dyn")
        if self.hands_open:
            c.create_oval(cx - CATCH_R, hy - CATCH_R, cx + CATCH_R, hy + CATCH_R,
                          outline="#2ecc71", dash=(3, 4), width=2, tags="dyn")

    def draw_hud(self, now):
        c = self.canvas
        info = LEVELS[self.level]
        state = "OPEN ✋" if self.hands_open else "CLOSED ✊"
        hand_col = "#2ecc71" if self.hands_open else "#ff8a80"

        c.create_rectangle(8, 48, 440, 192, fill="#000000", stipple="gray50", outline="", tags="dyn")
        c.create_text(16, 56, anchor="nw", fill="white", font=("Helvetica", 12, "bold"),
                      text=f"Level {self.level + 1}: {info['name']}", tags="dyn")
        c.create_text(16, 76, anchor="nw", fill="#ffe14d", font=("Helvetica", 13, "bold"),
                      text=(f"{self.p1_name} (Thrower): {self.p1_total + self.p1_level}      "
                            f"{self.p2_name} (Catcher): {self.p2_total + self.level_score}"), tags="dyn")
        tl = max(0, int(self.level_end - now))
        c.create_text(16, 98, anchor="nw", fill="white", font=("Helvetica", 12),
                      text=f"Throws left: {self.throws_left}      Time: {tl // 60}:{tl % 60:02d}",
                      tags="dyn")
        c.create_text(16, 118, anchor="nw", fill="#cfe0ff", font=("Helvetica", 11),
                      text=fmt_params(self.level, self.p), tags="dyn")
        c.create_text(16, 138, anchor="nw", fill="#cfe0ff", font=("Helvetica", 11),
                      text=f"→ Range {self.res['R']:.1f} m    Max height {self.res['H']:.1f} m    "
                           f"Time {self.res['T']:.2f} s", tags="dyn")
        c.create_text(16, 160, anchor="nw", fill=hand_col, font=("Helvetica", 12, "bold"),
                      text=f"{'AI' if self.mode == 'single' else 'P2'} hands: {state}", tags="dyn")
        # key help strip
        if self.level == 0:
            p1 = "W/S start height   A/D near/far"
        elif self.level == 1:
            p1 = "W/S height   A/D near/far"
        else:
            p1 = "W/S height   A/D near/far   Q/E start height"
        c.create_rectangle(0, H_CANVAS - 40, W, H_CANVAS, fill="#000000", stipple="gray50",
                           outline="", tags="dyn")
        c.create_text(W // 2, H_CANVAS - 29, fill="white", font=("Helvetica", 11, "bold"),
                      text=f"{'YOU' if self.mode == 'single' else 'P1'} THROWER:  {p1}   F = volleyball   G = basketball", tags="dyn")
        c.create_text(W // 2, H_CANVAS - 11, fill="white", font=("Helvetica", 11, "bold"),
                      text=("AI CATCHER:  moves and opens its hands by itself" if self.mode == "single"
                        else "P2 CATCHER:  Arrow keys = move   SPACE = open / close hands"), tags="dyn")

        if abs(play_speed(self.res) - 1) > 0.02:
            c.create_text(W - 10, 50, anchor="ne", fill="white", font=("Helvetica", 10),
                          text=f"Playback speed: {play_speed(self.res):.3g}× real time", tags="dyn")
        c.create_text(W - 10, 66, anchor="ne", fill="white", font=("Helvetica", 10),
                      text="Catcher:  Volleyball +10  |  Basketball −10", tags="dyn")

    # ---- balls
    def spawn(self, kind, now):
        res = self.res
        self.report_res, self.report_p = res, dict(self.p)
        if kind == "V":
            aim = random.random() < AI_SEES_V         # AI sometimes ignores a volleyball
        else:
            aim = random.random() < AI_SEES_B         # ...and sometimes grabs a basketball
        px, py = to_px(0, res["y0"], self.scale)
        self.balls.append({
            "kind": kind, "t0": now, "state": "fly", "land": 0.0,
            "res": res, "scale": self.scale, "speed": play_speed(res),
            "px": px, "py": py,
            "ai_aim": aim,
            "ai_react": now + random.uniform(*AI_REACT),
            "ai_dx": max(-2 * AI_ERR, min(2 * AI_ERR, random.gauss(0, AI_ERR))),
            "ai_dy": max(-2 * AI_ERR, min(2 * AI_ERR, random.gauss(0, AI_ERR))),
        })

    def throw(self, kind, now):
        """Multiplayer: Player 1 throws a ball."""
        if self.throws_left <= 0 or now - self.last_throw < THROW_COOLDOWN:
            return
        self.last_throw = now
        self.throws_left -= 1
        self.spawn(kind, now)

    # ---- player control (multiplayer)
    def player_control(self, dt):
        k = self.keys
        sp = PLAYER_SPEED * dt
        self.cx += sp * (("Right" in k) - ("Left" in k))
        self.chy += sp * (("Down" in k) - ("Up" in k))
        self.adjust_params(dt)

    def adjust_params(self, dt):
        """The thrower fine-tunes the trajectory live: W/S height, A/D distance."""
        k, lvl = self.keys, self.level
        q = dict(self.p)
        far = ("d" in k) - ("a" in k)      # D = throw farther, A = throw nearer
        up = ("w" in k) - ("s" in k)       # W = higher, S = lower
        he = ("e" in k) - ("q" in k)       # E / Q = starting height (level 3)
        if lvl == 0:
            # horizontal launch: A/D = launch speed (distance), W/S = launch height
            if far:
                q["v"] = min(150.0, max(1.0, q["v"] + far * 12 * dt))
            if up:
                q["h"] = min(200.0, max(0.5, q["h"] + up * 10 * dt))
        else:
            # angled launch: A/D changes only the horizontal speed (distance),
            # W/S changes only the vertical speed (how high the ball goes)
            if far or up:
                ang = math.radians(q["a"])
                vx, vy = q["v"] * math.cos(ang), q["v"] * math.sin(ang)
                vx = min(100.0, max(0.5, vx + far * 12 * dt))
                vy = min(100.0, max(0.5 if lvl == 1 else -100.0, vy + up * 12 * dt))
                q["v"] = math.hypot(vx, vy)
                q["a"] = math.degrees(math.atan2(vy, vx))
            if lvl == 2 and he:
                q["h"] = min(200.0, max(0.0, q["h"] + he * 10 * dt))
        if q == self.p:
            return
        try:
            res = compute(lvl, q)
            ok = all(math.isfinite(res[x]) for x in ("R", "H", "T")) and res["T"] > 1e-9
        except (ValueError, ZeroDivisionError, OverflowError):
            ok = False
        if ok:
            self.p, self.res, self.scale = q, res, calc_scale(res)

    # ---- AI control (single player)
    @staticmethod
    def ball_px(b, ts):
        x, y = pos_at(b["res"], min(ts, b["res"]["T"]))
        return to_px(x, max(y, 0), b["scale"])

    def ai_control(self, now, dt):
        aim_balls = [b for b in self.balls
                     if b["state"] == "fly" and b["ai_aim"] and now >= b["ai_react"]]

        # nearest ball the AI wants to catch
        nearest, nd = None, 1e9
        for b in aim_balls:
            d = math.hypot(b["px"] - self.cx, b["py"] - self.chy)
            if d < nd:
                nearest, nd = b, d

        tgt = None
        if nearest is not None and nd < CATCH_R * 2.4:
            # close range: lock onto the ball (a hair ahead of it)
            b = nearest
            ts = (now - b["t0"]) * b["speed"] + 0.06 * b["speed"]
            px, py = self.ball_px(b, ts)
            tgt = (max(30, min(W - 30, px + b["ai_dx"])),
                   max(60, min(GROUND_Y - 40, py + b["ai_dy"])))
        else:
            # planning: earliest point on a trajectory the AI can reach in time
            plan = None
            for b in aim_balls:
                T, sp = b["res"]["T"], b["speed"]
                ts = (now - b["t0"]) * sp
                left = (T - ts) / sp
                if left <= 0:
                    continue
                found, last = None, None
                N = 36
                for i in range(N + 1):
                    tr = left * i / N
                    px, py = self.ball_px(b, ts + tr * sp)
                    px += b["ai_dx"]
                    py += b["ai_dy"]
                    tx = max(30, min(W - 30, px))
                    ty = max(60, min(GROUND_Y - 40, py))
                    last = (tx, ty)
                    if math.hypot(tx - px, ty - py) > CATCH_R * 0.4:
                        continue                     # point is out of reach
                    need = max(abs(tx - self.cx), abs(ty - self.chy)) / AI_SPEED + AI_PLAN_LAG
                    if need <= tr:
                        found = (tr, tx, ty)
                        break
                if found is None and last is not None:
                    found = (left, last[0], last[1])  # can't make it: head for the landing spot
                if found and (plan is None or found[0] < plan[0]):
                    plan = found
            if plan:
                tgt = (plan[1], plan[2])
        if tgt is None:
            tgt = self.idle

        step = AI_SPEED * dt
        self.cx += max(-step, min(step, tgt[0] - self.cx))
        self.chy += max(-step, min(step, tgt[1] - self.chy))

        # hands: open only when the wanted ball is close and no unwanted basketball is near
        danger = any(b["kind"] == "B" and not b["ai_aim"] and b["state"] == "fly"
                     and math.hypot(b["px"] - self.cx, b["py"] - self.chy) < CATCH_R + 14
                     for b in self.balls)
        self.hands_open = nearest is not None and nd <= CATCH_R * 1.3 and not danger

    # ---- main loop
    def tick(self):
        if not self.running:
            return
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        single = self.mode == "single"

        if single:
            self.ai_control(now, dt)
            self.adjust_params(dt)          # you steer the trajectory
        else:
            self.player_control(dt)
        self.cx = max(30, min(W - 30, self.cx))
        self.chy = max(60, min(GROUND_Y - 40, self.chy))

        # time limit
        if now >= self.level_end and self.throws_left > 0:
            self.throws_left = 0
            self.popups.append({"text": "Time's up!", "color": "#ffe14d", "x": W // 2, "y": 200, "t": now})

        # update balls
        for b in self.balls[:]:
            if b["state"] == "fly":
                res = b["res"]
                T = res["T"]
                ts = (now - b["t0"]) * b["speed"]
                landed = ts >= T
                if landed:
                    ts = T
                x, y = pos_at(res, ts)
                b["px"], b["py"] = to_px(x, max(y, 0), b["scale"])
                if self.hands_open and math.hypot(b["px"] - self.cx, b["py"] - self.chy) < CATCH_R:
                    self.catch(b, now)
                    continue
                if landed:
                    b["state"], b["land"] = "landed", now
                    self.on_land(b, now)
            elif now - b["land"] > 0.7:
                self.balls.remove(b)

        # draw
        c = self.canvas
        c.delete("dyn")
        self.draw_guide()
        self.draw_thrower()
        for b in self.balls:
            self.draw_ball(b["px"], b["py"], b["kind"])
        self.draw_catcher()
        for pu in self.popups[:]:
            age = now - pu["t"]
            if age > 1.0:
                self.popups.remove(pu)
                continue
            c.create_text(pu["x"], pu["y"] - 60 * age, text=pu["text"], fill=pu["color"],
                          font=("Helvetica", 20, "bold"), tags="dyn")
        self.draw_hud(now)

        done = self.throws_left <= 0
        if done and not self.balls and not self.finishing:
            self.finishing = True
            self.after(600, self.finish_level)
        self._job = self.after(16, self.tick)

    def catch(self, b, now):
        self.balls.remove(b)
        if b["kind"] == "V":
            self.level_score += 10
            self.caught_v += 1
            self.popups.append({"text": "+10  Volleyball!", "color": "#1b9e3e",
                                "x": self.cx, "y": self.chy - 30, "t": now})
        else:
            self.level_score -= 10
            self.caught_b += 1
            self.p1_level += 10
            self.popups.append({"text": f"−10  Basketball!  ({self.p1_name} +10)",
                                "color": "#d62828", "x": self.cx, "y": self.chy - 30, "t": now})

    def on_land(self, b, now):
        """A ball hit the floor without being caught."""
        if b["kind"] == "V":
            self.p1_level += 10
            self.popups.append({"text": f"Dropped!  {self.p1_name} +10", "color": "#e67e22",
                                "x": min(max(b["px"], 100), W - 100), "y": b["py"] - 30, "t": now})

    def finish_level(self):
        self.running = False
        self.p1_total += self.p1_level
        self.p2_total += self.level_score
        self.show_results()

    # ---- keyboard
    def on_key_press(self, ev):
        k = ev.keysym
        if k == "space":
            now = time.perf_counter()
            if self.running and self.mode == "multi" and now - self.last_space > 0.15:
                self.hands_open = not self.hands_open
                self.last_space = now
            return
        key = k if k in ARROWS else k.lower()
        self.keys.add(key)
        if self.running and key in ("f", "g"):
            self.throw("V" if key == "f" else "B", time.perf_counter())

    def on_key_release(self, ev):
        k = ev.keysym
        self.keys.discard(k if k in ARROWS else k.lower())

    # --------------------------------------------------------- results page
    def show_results(self):
        r = self.report_res or self.res
        f = self.blue_frame()
        tk.Label(f, text=f"Level {self.level + 1} Complete!  —  {LEVELS[self.level]['name']}",
                 bg=BLUE, fg="white", font=("Helvetica", 24, "bold")).pack(pady=(26, 6))
        score = (f"{self.p1_name} (Thrower): +{self.p1_level}    "
                 f"{self.p2_name} (Catcher): {self.level_score:+d}    "
                 f"(volleyballs caught: {self.caught_v}, basketballs caught: {self.caught_b})")
        tot = f"Totals  —  {self.p1_name}: {self.p1_total}     {self.p2_name}: {self.p2_total}"
        tk.Label(f, text=score, bg=BLUE, fg="#ffe14d", font=("Helvetica", 14, "bold")).pack()
        tk.Label(f, text=tot, bg=BLUE, fg="#ffe14d", font=("Helvetica", 15, "bold")).pack(pady=(2, 0))
        tk.Label(f, text="Physics for the last throw:  " + fmt_params(self.level, self.report_p),
                 bg=BLUE, fg="#cfe0ff", font=("Helvetica", 12)).pack(pady=(6, 8))

        box = tk.Frame(f, bg=PANEL, padx=20, pady=12)
        box.pack(padx=30, fill="x")
        for name, formula, val, unit in r["lines"]:
            tk.Label(box, text=f"{name}:   {val:.4f} {unit}", bg=PANEL, fg="white",
                     font=("Helvetica", 17, "bold"), anchor="w", justify="left").pack(fill="x", pady=(8, 0))
            tk.Label(box, text=f"{formula} = {val:.4f} {unit}", bg=PANEL, fg="#cfe0ff",
                     font=("Helvetica", 11), anchor="w", justify="left", wraplength=900).pack(fill="x")
        general, specific = r["traj"]
        tk.Label(box, text="Trajectory:", bg=PANEL, fg="white",
                 font=("Helvetica", 17, "bold"), anchor="w").pack(fill="x", pady=(8, 0))
        tk.Label(box, text=general, bg=PANEL, fg="#cfe0ff", font=("Helvetica", 11),
                 anchor="w").pack(fill="x")
        tk.Label(box, text=specific + "      (x, y in meters)", bg=PANEL, fg="#ffe14d",
                 font=("Helvetica", 14, "bold"), anchor="w", wraplength=900, justify="left").pack(fill="x")

        last = self.level == len(LEVELS) - 1
        if last:
            if self.p1_total > self.p2_total:
                verdict = "You win!" if self.mode == "single" else "Player 1 (Thrower) wins!"
            elif self.p2_total > self.p1_total:
                verdict = "The AI wins!" if self.mode == "single" else "Player 2 (Catcher) wins!"
            else:
                verdict = "It's a tie!"
            msg = f"🏆 GAME OVER — {verdict}"
            tk.Label(f, text=msg, bg=BLUE, fg="white",
                     font=("Helvetica", 22, "bold")).pack(pady=(16, 4))
            row = tk.Frame(f, bg=BLUE)
            row.pack(pady=6)
            tk.Button(row, text="Play Again", font=("Helvetica", 16, "bold"), width=12,
                      command=self.new_game).pack(side="left", padx=8)
            tk.Button(row, text="Main Menu", font=("Helvetica", 16, "bold"), width=12,
                      command=self.show_mode_select).pack(side="left", padx=8)
            tk.Button(row, text="Quit", font=("Helvetica", 16, "bold"), width=12,
                      command=self.destroy).pack(side="left", padx=8)
        else:
            tk.Button(f, text="Next Level  ▶", font=("Helvetica", 18, "bold"), width=16,
                      command=self.next_level).pack(pady=20)

    def next_level(self):
        self.level += 1
        self.show_input()


if __name__ == "__main__":
    App().mainloop()
