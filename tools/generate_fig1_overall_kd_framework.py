"""Generate a compact, publication-ready Teacher-Student KD framework.

The SVG and PDF contain only vector primitives and text. The PNG is exported
separately at 600 dpi. All visual settings and reported metrics are centralized
below so the figure can be adapted without changing the drawing logic.
"""

from pathlib import Path
import re

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.path import Path as MplPath


# -----------------------------------------------------------------------------
# Global, editable figure specification
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "fig1_overall_kd_framework.svg"
PDF_PATH = ROOT / "fig1_overall_kd_framework.pdf"
PNG_PATH = ROOT / "fig1_overall_kd_framework_600dpi.png"

WIDTH_MM = 174.0
HEIGHT_MM = 98.0
FONT = "Arial"

FS_TINY = 7.0
FS_SMALL = 7.6
FS_BODY = 8.2
FS_HEAD = 9.2

LINE = 0.9
ARROW_LINE = 1.05
ARROW_SCALE = 9.5
RADIUS = 1.6

COLOR = {
    "ink": "#17212B",
    "muted": "#5D6872",
    "line": "#8B959E",
    "teacher": "#28518A",
    "teacher_dark": "#17365F",
    "teacher_fill": "#F2F6FB",
    "student": "#147D75",
    "student_dark": "#0B5954",
    "student_fill": "#EFF8F6",
    "loss": "#B96A13",
    "loss_dark": "#7B4308",
    "loss_fill": "#FFF7EA",
    "optional": "#747C83",
    "neutral_fill": "#F5F6F7",
    "white": "#FFFFFF",
}

# Strictly paired RAF-DB result: VAE/KLD teacher -> 224 LightLE-VICH student.
TEACHER_STATS = "58.33M params   |   8.48G MACs   |   91.82% acc."
STUDENT_STATS = "2.25M params   |   0.33G MACs   |   90.06% acc."


def configure_style():
    """Configure typography and vector-export behavior."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [FONT, "Helvetica", "DejaVu Sans"],
            "font.size": FS_BODY,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def draw_label(
    ax,
    x,
    y,
    text,
    *,
    size=FS_BODY,
    color=None,
    weight="normal",
    ha="center",
    va="center",
    rotation=0,
    zorder=8,
):
    """Draw one consistently styled label."""
    return ax.text(
        x,
        y,
        text,
        fontsize=size,
        color=color or COLOR["ink"],
        fontweight=weight,
        ha=ha,
        va=va,
        rotation=rotation,
        linespacing=1.15,
        zorder=zorder,
    )


def draw_box(
    ax,
    x,
    y,
    width,
    height,
    text="",
    *,
    facecolor=None,
    edgecolor=None,
    textcolor=None,
    linewidth=LINE,
    linestyle="solid",
    fontsize=FS_BODY,
    weight="normal",
    radius=RADIUS,
    zorder=3,
):
    """Draw a rounded module box with optional centered text."""
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=facecolor or COLOR["white"],
        edgecolor=edgecolor or COLOR["ink"],
        linewidth=linewidth,
        linestyle=linestyle,
        zorder=zorder,
    )
    ax.add_patch(patch)
    if text:
        draw_label(
            ax,
            x + width / 2,
            y + height / 2,
            text,
            size=fontsize,
            color=textcolor or COLOR["ink"],
            weight=weight,
            zorder=zorder + 1,
        )
    return patch


def draw_arrow(
    ax,
    start,
    end,
    *,
    color=None,
    linewidth=ARROW_LINE,
    linestyle="solid",
    connectionstyle="arc3,rad=0",
    zorder=5,
):
    """Draw a clean directed connection."""
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=ARROW_SCALE,
        color=color or COLOR["ink"],
        linewidth=linewidth,
        linestyle=linestyle,
        connectionstyle=connectionstyle,
        shrinkA=0,
        shrinkB=0,
        zorder=zorder,
    )
    ax.add_patch(arrow)
    return arrow


def draw_routed_arrow(
    ax,
    points,
    *,
    color,
    linewidth=ARROW_LINE,
    linestyle="solid",
    zorder=4,
):
    """Draw an orthogonal arrow through explicit waypoints."""
    path = MplPath(
        list(points),
        [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1),
    )
    arrow = FancyArrowPatch(
        path=path,
        arrowstyle="-|>",
        mutation_scale=ARROW_SCALE,
        color=color,
        linewidth=linewidth,
        linestyle=linestyle,
        shrinkA=0,
        shrinkB=0,
        zorder=zorder,
    )
    ax.add_patch(arrow)
    return arrow


def draw_info_box(ax, x, y, width, title, stats, accent, fill):
    """Draw a branch header with a concise metric line."""
    ax.add_patch(Rectangle((x, y), width, 8.5, facecolor=fill, edgecolor="none", zorder=4))
    ax.add_patch(Rectangle((x, y + 7.7), width, 0.8, facecolor=accent, edgecolor="none", zorder=5))
    draw_label(ax, x + 2.5, y + 5.5, title, size=FS_HEAD, color=accent, weight="bold", ha="left")
    draw_label(ax, x + 2.5, y + 2.1, stats, size=FS_TINY, color=COLOR["muted"], weight="bold", ha="left")


def draw_stage(ax, x, y, width, text, accent, fill, *, dashed=False):
    """Draw a single network stage."""
    return draw_box(
        ax,
        x,
        y,
        width,
        10.5,
        text,
        facecolor=fill,
        edgecolor=accent,
        textcolor=accent,
        linewidth=0.9,
        linestyle="dashed" if dashed else "solid",
        fontsize=FS_SMALL,
        weight="bold",
        radius=1.25,
    )


def draw_branch(
    ax,
    *,
    x,
    y,
    width,
    height,
    title,
    stats,
    accent,
    dark,
    fill,
    stages,
):
    """Draw a complete teacher or student processing card."""
    draw_box(
        ax,
        x,
        y,
        width,
        height,
        facecolor=COLOR["white"],
        edgecolor=accent,
        linewidth=1.15,
        radius=2.0,
        zorder=1,
    )
    draw_info_box(ax, x, y + height - 8.5, width, title, stats, accent, fill)

    stage_y = y + 3.0
    gap = 3.0
    cursor = x + 3.0
    stage_boxes = []
    for label, stage_width in stages:
        stage_boxes.append(draw_stage(ax, cursor, stage_y, stage_width, label, dark, fill))
        cursor += stage_width + gap

    for left, right in zip(stage_boxes[:-1], stage_boxes[1:]):
        start = (left.get_x() + left.get_width(), stage_y + 5.25)
        end = (right.get_x(), stage_y + 5.25)
        draw_arrow(ax, start, end, color=dark, linewidth=0.95)
    return stage_boxes


def draw_objective(ax):
    """Draw the central multi-term training objective."""
    x, y, width, height = 137.0, 43.0, 33.0, 37.0
    draw_box(
        ax,
        x,
        y,
        width,
        height,
        facecolor=COLOR["loss_fill"],
        edgecolor=COLOR["loss_dark"],
        linewidth=1.25,
        radius=2.0,
        zorder=2,
    )
    ax.add_patch(Rectangle((x, y + height - 6.5), width, 6.5, facecolor=COLOR["loss_fill"], edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((x, y + height - 0.8), width, 0.8, facecolor=COLOR["loss"], edgecolor="none", zorder=4))
    draw_label(ax, x + width / 2, y + height - 3.3, "Training objective", size=FS_HEAD, color=COLOR["loss_dark"], weight="bold")

    rows = [
        (y + 25.5, "CE loss  (hard labels)", False),
        (y + 19.0, "KD / KL loss  (temperature T)", False),
        (y + 12.5, "VICH uncertainty loss", True),
        (y + 6.0, "Feature alignment\n(optional, lambda_f = 0)", True),
    ]
    for yy, text, optional in rows:
        if yy != rows[0][0]:
            ax.plot([x + 3.0, x + width - 3.0], [yy + 3.2, yy + 3.2], color="#DFC9A8", linewidth=0.45, zorder=4)
        draw_label(ax, x + width / 2, yy, text, size=FS_SMALL, color=COLOR["optional"] if optional else COLOR["ink"], weight="bold")

    return (x, y, width, height)


def normalize_svg_size(path):
    """Store explicit physical dimensions for Word and LaTeX import."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'(<svg[^>]*?)width="[^"]+" height="[^"]+"',
        rf'\1width="{WIDTH_MM:g}mm" height="{HEIGHT_MM:g}mm"',
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def build_figure():
    """Build the complete two-branch KD framework."""
    configure_style()
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), facecolor=COLOR["white"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH_MM)
    ax.set_ylim(0, HEIGHT_MM)
    ax.set_aspect("equal")
    ax.axis("off")

    # Shared image and label inputs.
    draw_box(
        ax,
        3.5,
        43.0,
        18.5,
        14.0,
        "Input facial\nimage  x",
        facecolor=COLOR["neutral_fill"],
        edgecolor=COLOR["ink"],
        textcolor=COLOR["ink"],
        linewidth=1.05,
        fontsize=FS_BODY,
        weight="bold",
    )
    draw_box(
        ax,
        5.0,
        32.5,
        15.5,
        6.0,
        "Ground truth  y",
        facecolor=COLOR["white"],
        edgecolor=COLOR["line"],
        textcolor=COLOR["muted"],
        linewidth=0.75,
        fontsize=FS_TINY,
        radius=3.0,
    )

    teacher_boxes = draw_branch(
        ax,
        x=29.0,
        y=62.0,
        width=88.0,
        height=27.0,
        title="POSTER-Var teacher",
        stats=TEACHER_STATS,
        accent=COLOR["teacher"],
        dark=COLOR["teacher_dark"],
        fill=COLOR["teacher_fill"],
        stages=[
            ("IR50 +\nlandmarks", 18.0),
            ("Pyramid cross-\nattention", 22.0),
            ("Transformer\nfusion", 18.0),
            ("VAE / KLD\nhead", 16.0),
        ],
    )
    student_boxes = draw_branch(
        ax,
        x=29.0,
        y=18.0,
        width=88.0,
        height=27.0,
        title="MobileNetV2Plus student",
        stats=STUDENT_STATS,
        accent=COLOR["student"],
        dark=COLOR["student_dark"],
        fill=COLOR["student_fill"],
        stages=[
            ("MobileNetV2\n+ ECA", 21.0),
            ("GeM\npooling", 15.0),
            ("LightLE\nfusion", 18.0),
            ("VICH\nhead", 14.0),
        ],
    )

    # Output capsules make the transferred information explicit.
    draw_box(
        ax,
        120.0,
        68.0,
        12.5,
        11.0,
        "z_t  /  p_t\nuncertainty u_t",
        facecolor=COLOR["teacher_fill"],
        edgecolor=COLOR["teacher_dark"],
        textcolor=COLOR["teacher_dark"],
        linewidth=1.0,
        fontsize=FS_TINY,
        weight="bold",
        radius=5.0,
    )
    draw_box(
        ax,
        120.0,
        24.0,
        12.5,
        11.0,
        "z_s\nmu_s, logvar_s",
        facecolor=COLOR["student_fill"],
        edgecolor=COLOR["student_dark"],
        textcolor=COLOR["student_dark"],
        linewidth=1.0,
        fontsize=FS_TINY,
        weight="bold",
        radius=5.0,
    )
    draw_arrow(ax, (117.0, 71.25), (120.0, 73.5), color=COLOR["teacher_dark"])
    draw_arrow(ax, (117.0, 27.25), (120.0, 29.5), color=COLOR["student_dark"])

    # Shared input is split once and routed into both branches.
    draw_routed_arrow(ax, [(22.0, 52.0), (25.0, 52.0), (25.0, 75.25), (29.0, 75.25)], color=COLOR["teacher_dark"])
    draw_routed_arrow(ax, [(22.0, 48.0), (25.0, 48.0), (25.0, 31.25), (29.0, 31.25)], color=COLOR["student_dark"])

    objective = draw_objective(ax)
    ox, oy, ow, oh = objective

    # Teacher and student predictions meet at the objective.
    draw_routed_arrow(ax, [(132.5, 73.5), (134.5, 73.5), (134.5, 62.0), (ox, 62.0)], color=COLOR["teacher_dark"])
    draw_routed_arrow(ax, [(132.5, 29.5), (134.5, 29.5), (134.5, 56.0), (ox, 56.0)], color=COLOR["student_dark"])
    draw_routed_arrow(ax, [(20.5, 35.5), (27.0, 35.5), (27.0, 68.5), (ox, 68.5)], color=COLOR["ink"], linewidth=0.9)

    # Optional feature alignment is visually subordinate and disabled (lambda=0).
    teacher_feature = (
        teacher_boxes[2].get_x() + teacher_boxes[2].get_width(),
        teacher_boxes[2].get_y() + 1.0,
    )
    student_feature = (
        student_boxes[2].get_x() + student_boxes[2].get_width(),
        student_boxes[2].get_y() + student_boxes[2].get_height() - 1.0,
    )
    draw_routed_arrow(ax, [teacher_feature, (112.5, 58.0), (ox, 49.0)], color=COLOR["optional"], linewidth=0.7, linestyle="dotted", zorder=2)
    draw_routed_arrow(ax, [student_feature, (112.5, 50.0), (ox, 49.0)], color=COLOR["optional"], linewidth=0.7, linestyle="dotted", zorder=2)
    draw_label(ax, 116.0, 53.8, "optional feature pair", size=FS_TINY, color=COLOR["optional"], rotation=90)

    # Only the student receives gradients.
    draw_routed_arrow(
        ax,
        [(137.0, 47.0), (134.0, 47.0), (134.0, 13.0), (100.0, 13.0), (100.0, 18.0)],
        color=COLOR["loss_dark"],
        linewidth=1.05,
        linestyle="dashed",
        zorder=3,
    )
    draw_label(ax, 116.5, 11.0, "back-propagation: student only", size=FS_TINY, color=COLOR["loss_dark"], weight="bold")

    # Inference path remains independent of the training objective.
    draw_box(
        ax,
        138.5,
        18.0,
        30.0,
        14.0,
        "Emotion prediction\n7 / 8 emotion classes",
        facecolor=COLOR["white"],
        edgecolor=COLOR["student_dark"],
        textcolor=COLOR["student_dark"],
        linewidth=1.15,
        fontsize=FS_BODY,
        weight="bold",
        radius=2.0,
    )
    draw_arrow(ax, (132.5, 28.0), (138.5, 25.0), color=COLOR["student_dark"])

    # Compact objective notation below the objective card.
    draw_label(
        ax,
        152.0,
        38.3,
        "L = alpha L_CE + (1-alpha) L_KD\n+ beta L_VICH + lambda_f L_feature",
        size=FS_TINY,
        color=COLOR["loss_dark"],
        weight="bold",
    )
    draw_label(
        ax,
        29.0,
        7.0,
        "Solid paths: active in the reported run     Dotted path: optional feature loss (lambda_f = 0)",
        size=FS_TINY,
        color=COLOR["optional"],
        ha="left",
    )

    return fig


def main():
    """Generate SVG, PDF and 600 dpi PNG outputs."""
    figure = build_figure()
    figure.savefig(SVG_PATH, format="svg", facecolor=COLOR["white"], transparent=False)
    normalize_svg_size(SVG_PATH)
    figure.savefig(PDF_PATH, format="pdf", facecolor=COLOR["white"], transparent=False)
    figure.savefig(PNG_PATH, format="png", dpi=600, facecolor=COLOR["white"], transparent=False)
    plt.close(figure)

    print(f"Saved vector SVG: {SVG_PATH}")
    print(f"Saved vector PDF: {PDF_PATH}")
    print(f"Saved 600 dpi PNG: {PNG_PATH}")


if __name__ == "__main__":
    main()
