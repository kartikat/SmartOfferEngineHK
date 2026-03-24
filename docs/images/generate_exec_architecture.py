"""
Executive Architecture Diagram for SmartOfferEngine
Generates: exec_architecture.png
Uses only matplotlib patches + text — no emoji dependency.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

# ── Canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 1600)
ax.set_ylim(0, 900)
ax.set_aspect('equal')
ax.axis('off')
fig.patch.set_facecolor('white')

# ── Brand colours ─────────────────────────────────────────────────────────────
ALB_BLUE   = '#00529B'
ALB_RED    = '#E31837'
FILL_LBLUE = '#EBF4FF'
FILL_LGRN  = '#EDFAF1'
ARROW_CLR  = '#00529B'
TEXT_DARK  = '#1A1A2E'
GREY_TEXT  = '#6B7280'
GREEN_BDR  = '#16A34A'
STRIP_BG   = '#F8F9FA'
DARK_GREEN = '#14532D'

# ── Layout constants ───────────────────────────────────────────────────────────
PAD        = 28
ARROW_W    = 44
STRIP_H    = 152
HEADER_H   = 44
BOX_Y_TOP  = HEADER_H + 10          # gap below header
BOX_H      = 900 - BOX_Y_TOP - STRIP_H - PAD - 20
BOX_W      = (1600 - 2 * PAD - 2 * ARROW_W) / 3   # ≈ 482

X1 = PAD
X2 = X1 + BOX_W + ARROW_W
X3 = X2 + BOX_W + ARROW_W

BOX_TOP_Y  = 900 - BOX_Y_TOP        # data coords, y=0 at bottom
BOX_BOT_Y  = BOX_TOP_Y - BOX_H
BOX_MID_Y  = (BOX_TOP_Y + BOX_BOT_Y) / 2

STRIP_TOP_Y = BOX_BOT_Y - PAD // 2
STRIP_BOT_Y = STRIP_TOP_Y - STRIP_H

# ── Helpers ───────────────────────────────────────────────────────────────────
def rounded_rect(ax, x, y, w, h, fc, ec, lw=2.5, r=18, alpha=1.0, zorder=2):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        linewidth=lw, edgecolor=ec, facecolor=fc,
        alpha=alpha, zorder=zorder,
    )
    ax.add_patch(p)
    return p

def big_arrow(ax, x0, x1, y, color, lw=5.5):
    ax.add_patch(FancyArrowPatch(
        (x0, y), (x1, y),
        arrowstyle='-|>',
        mutation_scale=30,
        linewidth=lw,
        color=color,
        zorder=5,
    ))

def dot(ax, cx, cy, r, color, zorder=5):
    ax.add_patch(Circle((cx, cy), r, color=color, zorder=zorder))

def icon_bullet(ax, cx, cy, label, bullet_color):
    """Draw a small filled circle bullet + label text."""
    dot(ax, cx, cy, 9, bullet_color, zorder=5)
    ax.text(cx, cy, label[:2],
            ha='center', va='center', fontsize=7,
            fontweight='bold', color='white', zorder=6)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER BAR
# ══════════════════════════════════════════════════════════════════════════════
ax.add_patch(FancyBboxPatch(
    (0, 900 - HEADER_H), 1600, HEADER_H,
    boxstyle="square,pad=0",
    linewidth=0, facecolor=ALB_BLUE, zorder=8,
))
ax.text(800, 900 - HEADER_H / 2,
        'SmartOfferEngine  \u2022  Executive Architecture Overview',
        ha='center', va='center', fontsize=13, fontweight='bold',
        color='white', zorder=9)

# Albertsons wordmark accent (red left strip)
ax.add_patch(FancyBboxPatch(
    (0, 900 - HEADER_H), 8, HEADER_H,
    boxstyle="square,pad=0",
    linewidth=0, facecolor=ALB_RED, zorder=9,
))

# ══════════════════════════════════════════════════════════════════════════════
# BOX 1 — Albertsons C360 Data Platform
# ══════════════════════════════════════════════════════════════════════════════
rounded_rect(ax, X1, BOX_BOT_Y, BOX_W, BOX_H,
             fc=FILL_LBLUE, ec=ALB_BLUE, lw=2.5, r=16)

# Top colour accent
rounded_rect(ax, X1, BOX_TOP_Y - 12, BOX_W, 12,
             fc=ALB_BLUE, ec=ALB_BLUE, lw=0, r=8, zorder=3)

ax.text(X1 + BOX_W / 2, BOX_TOP_Y - 36,
        'Albertsons C360\nData Platform',
        ha='center', va='top', fontsize=17, fontweight='bold',
        color=ALB_BLUE, linespacing=1.4, zorder=4)

ax.text(X1 + BOX_W / 2, BOX_TOP_Y - 98,
        'What we already know about every customer',
        ha='center', va='top', fontsize=11, color=GREY_TEXT,
        style='italic', zorder=4)

items1 = [
    ('TX',  '#00529B', 'Transaction History'),
    ('LY',  '#00529B', 'Loyalty Profile & Points'),
    ('SH',  '#00529B', 'Shopping Preferences'),
    ('CH',  '#00529B', 'Channel & Engagement'),
]
item_start_y = BOX_TOP_Y - 148
item_gap     = 80

for i, (code, color, label) in enumerate(items1):
    iy = item_start_y - i * item_gap
    # pill background
    rounded_rect(ax, X1 + 28, iy - 23, BOX_W - 56, 46,
                 fc='white', ec='white', lw=0, r=10, alpha=0.72, zorder=3)
    icon_bullet(ax, X1 + 60, iy + 1, code, color)
    ax.text(X1 + 82, iy + 1, label,
            ha='left', va='center', fontsize=13.5,
            color=TEXT_DARK, fontweight='medium', zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# ARROW 1 → 2
# ══════════════════════════════════════════════════════════════════════════════
big_arrow(ax, X1 + BOX_W + 6, X2 - 6, BOX_MID_Y, ARROW_CLR)
ax.text((X1 + BOX_W + X2) / 2, BOX_MID_Y + 20,
        'feeds', ha='center', va='bottom', fontsize=9,
        color=GREY_TEXT, style='italic', zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# BOX 2 — SmartOfferEngine
# ══════════════════════════════════════════════════════════════════════════════
# Drop shadow
rounded_rect(ax, X2 + 7, BOX_BOT_Y - 7, BOX_W, BOX_H,
             fc='#8899bb', ec='none', lw=0, r=18, alpha=0.18, zorder=1)

rounded_rect(ax, X2, BOX_BOT_Y, BOX_W, BOX_H,
             fc=ALB_BLUE, ec=ALB_BLUE, lw=0, r=18, zorder=2)

# Red top accent
rounded_rect(ax, X2, BOX_TOP_Y - 14, BOX_W, 14,
             fc=ALB_RED, ec=ALB_RED, lw=0, r=8, zorder=3)

ax.text(X2 + BOX_W / 2, BOX_TOP_Y - 48,
        'SmartOfferEngine',
        ha='center', va='top', fontsize=21, fontweight='bold',
        color='white', zorder=4)

ax.text(X2 + BOX_W / 2, BOX_TOP_Y - 96,
        'Personalisation at household scale',
        ha='center', va='top', fontsize=11, color='#BFD9F5',
        style='italic', zorder=4)

inner_items = [
    ('RB', '#E31837', 'Rule-Based Scoring',      '5 weighted signals + engagement boosts'),
    ('AI', '#16A34A', 'AI Propensity Model',     'XGBoost \u00b7 predicts redemption likelihood'),
    ('GR', '#F59E0B', 'Grocery Reward Ranking',  'Points-aware \u00b7 tier-gated offers'),
]
inner_h      = 108
inner_gap    = 16
inner_start  = BOX_TOP_Y - 136
inner_x      = X2 + 26
inner_w      = BOX_W - 52

for j, (code, dot_color, title, subtitle) in enumerate(inner_items):
    iy = inner_start - j * (inner_h + inner_gap)
    rounded_rect(ax, inner_x, iy - inner_h, inner_w, inner_h,
                 fc='white', ec='white', lw=0, r=10, alpha=0.13, zorder=3)
    icon_bullet(ax, inner_x + 26, iy - inner_h / 2 + 10, code, dot_color)
    ax.text(inner_x + 48, iy - inner_h / 2 + 14, title,
            ha='left', va='center', fontsize=13,
            fontweight='bold', color='white', zorder=5)
    ax.text(inner_x + 48, iy - inner_h / 2 - 12, subtitle,
            ha='left', va='center', fontsize=10,
            color='#BFD9F5', zorder=5)

ax.text(X2 + BOX_W / 2, BOX_BOT_Y + 22,
        '64 offers  \u00d7  120,000 households  \u2022  Updates nightly',
        ha='center', va='bottom', fontsize=9.5,
        color='#BFD9F5', style='italic', zorder=4)

# ══════════════════════════════════════════════════════════════════════════════
# ARROW 2 → 3
# ══════════════════════════════════════════════════════════════════════════════
big_arrow(ax, X2 + BOX_W + 6, X3 - 6, BOX_MID_Y, 'white')
ax.text((X2 + BOX_W + X3) / 2, BOX_MID_Y + 20,
        'delivers', ha='center', va='bottom', fontsize=9,
        color=GREY_TEXT, style='italic', zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# BOX 3 — Personalised for U Experience
# ══════════════════════════════════════════════════════════════════════════════
rounded_rect(ax, X3, BOX_BOT_Y, BOX_W, BOX_H,
             fc=FILL_LGRN, ec=GREEN_BDR, lw=2.5, r=16)

rounded_rect(ax, X3, BOX_TOP_Y - 12, BOX_W, 12,
             fc=GREEN_BDR, ec=GREEN_BDR, lw=0, r=8, zorder=3)

ax.text(X3 + BOX_W / 2, BOX_TOP_Y - 36,
        'Personalised for U\u2122\nExperience',
        ha='center', va='top', fontsize=17, fontweight='bold',
        color=DARK_GREEN, linespacing=1.4, zorder=4)

ax.text(X3 + BOX_W / 2, BOX_TOP_Y - 98,
        'Right offer \u00b7 Right customer \u00b7 Right time',
        ha='center', va='top', fontsize=11, color=GREY_TEXT,
        style='italic', zorder=4)

items3 = [
    ('APP', GREEN_BDR, 'Mobile & Web App'),
    ('CLIP', GREEN_BDR, 'One-tap Offer Clipping'),
    ('PTS', '#F59E0B', 'for U\u207a Loyalty Rewards'),
]

for i, (code, color, label) in enumerate(items3):
    iy = item_start_y - i * item_gap
    rounded_rect(ax, X3 + 28, iy - 23, BOX_W - 56, 46,
                 fc='white', ec='white', lw=0, r=10, alpha=0.78, zorder=3)
    icon_bullet(ax, X3 + 60, iy + 1, code[:2], color)
    ax.text(X3 + 82, iy + 1, label,
            ha='left', va='center', fontsize=13.5,
            color=TEXT_DARK, fontweight='medium', zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# BOTTOM IMPACT STRIP
# ══════════════════════════════════════════════════════════════════════════════
rounded_rect(ax, PAD, STRIP_BOT_Y, 1600 - 2 * PAD, STRIP_H,
             fc=STRIP_BG, ec='#D1D5DB', lw=1.5, r=12)

# Strip title
ax.text(800, STRIP_TOP_Y - 16,
        'Business Impact',
        ha='center', va='top', fontsize=14, fontweight='bold',
        color='#374151', zorder=4)

# Divider line
ax.plot([PAD + 20, 1600 - PAD - 20],
        [STRIP_TOP_Y - 40, STRIP_TOP_Y - 40],
        color='#D1D5DB', linewidth=1, zorder=3)

# 3 metric columns
metrics = [
    ('\u2191 Redemption Rate', 'More relevant offers = more clips',   ALB_BLUE),
    ('\u2193 Points Breakage',  'Customers redeem before expiry',      ALB_RED),
    ('\u2191 Basket Size',      'Right category, right moment',        GREEN_BDR),
]
col_w = (1600 - 2 * PAD) / 3
col_cx = [PAD + col_w * (k + 0.5) for k in range(3)]
metric_y = STRIP_BOT_Y + 66

for k, (big, small, clr) in enumerate(metrics):
    if k > 0:
        ax.plot([PAD + col_w * k, PAD + col_w * k],
                [STRIP_BOT_Y + 12, STRIP_TOP_Y - 44],
                color='#D1D5DB', linewidth=1, zorder=3)
    ax.text(col_cx[k], metric_y + 14, big,
            ha='center', va='center', fontsize=17, fontweight='bold',
            color=clr, zorder=5)
    ax.text(col_cx[k], metric_y - 20, small,
            ha='center', va='center', fontsize=11,
            color=GREY_TEXT, zorder=5)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
ax.text(800, 7,
        'SmartOfferEngine  \u00b7  Albertsons Hackathon 2026',
        ha='center', va='bottom', fontsize=9,
        color='#9CA3AF', zorder=4)

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = '/Users/KartikaT/HackathonProject/docs/images/exec_architecture.png'
fig.savefig(out_path, dpi=150, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close(fig)
print(f'Saved: {out_path}')
