"""Esportazione delle share e delle ricostruzioni come immagini PNG."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .protocol import Construction, Evaluation, Transfer
from .visual import BinaryImage, pointer_block, read_pointer


@dataclass(frozen=True)
class PrintableSegment:
    """Intervallo orizzontale espresso in pixel logici del protocollo."""

    label: str
    start: int
    width: int


@dataclass(frozen=True)
class ShareLayout:
    """Share componibile per la stampa; `split_at` è il taglio fra le due metà."""

    pixels: BinaryImage
    segments: tuple[PrintableSegment, ...]
    split_at: int | None = None


def image_to_pil(image: np.ndarray, *, scale: int = 8) -> Image.Image:
    if scale < 1 or scale > 64:
        raise ValueError("La scala deve essere compresa tra 1 e 64.")
    pixels = np.asarray(image, dtype=np.uint8)
    if pixels.ndim != 2:
        raise ValueError("È richiesta una matrice bidimensionale.")
    grayscale = ((1 - pixels) * 255).astype(np.uint8)
    result = Image.fromarray(grayscale)
    if scale != 1:
        result = result.resize(
            (result.width * scale, result.height * scale),
            resample=Image.Resampling.NEAREST,
        )
    return result


def image_png_bytes(image: np.ndarray, *, scale: int = 8) -> bytes:
    stream = BytesIO()
    image_to_pil(image, scale=scale).save(stream, format="PNG")
    return stream.getvalue()


def pointer_parts(
    role: str,
    pointer_value: BinaryImage,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Separa il pointer in chiaro dalle share dei pointer delle porte superiori."""
    selected = tuple(int(bit) for bit in pointer_value.tolist())
    if role == "left" and len(selected) >= 2:
        clear = read_pointer(np.asarray(selected[:2], dtype=np.uint8))
        return (clear,), selected[2:]
    return (), selected


def share_layout(
    main: BinaryImage,
    role: str,
    pointer_value: BinaryImage,
) -> ShareLayout:
    """Compone una share e i suoi pointer mantenendo la geometria del paper."""
    main = np.asarray(main, dtype=np.uint8)
    if main.ndim != 2:
        raise ValueError("La share principale deve essere bidimensionale.")
    clear_bits, inner_bits = pointer_parts(role, pointer_value)

    segments: list[PrintableSegment] = []

    def compose(parts: list[tuple[str, BinaryImage, bool]]) -> BinaryImage:
        width = sum(
            part.size if is_pointer else part.shape[1]
            for _, part, is_pointer in parts
        )
        canvas = np.zeros((main.shape[0], width), dtype=np.uint8)
        cursor = 0
        for label, part, is_pointer in parts:
            part_width = part.size if is_pointer else part.shape[1]
            if part_width:
                if is_pointer:
                    canvas[-1, cursor : cursor + part_width] = part.reshape(-1)
                else:
                    canvas[:, cursor : cursor + part_width] = part
                segments.append(PrintableSegment(label, cursor, part_width))
            cursor += part_width
        return canvas

    if role == "left":
        clear_pixels = (
            np.concatenate([pointer_block(bit) for bit in clear_bits])
            if clear_bits
            else np.zeros(0, dtype=np.uint8)
        )
        inner_pixels = np.asarray(inner_bits, dtype=np.uint8)
        if inner_pixels.size % 2:
            raise ValueError(
                "Le share dei pointer delle porte superiori devono essere coppie 1×2."
            )
        pixels = compose(
            [
                ("pointer in chiaro", clear_pixels, True),
                ("share pointer porte superiori", inner_pixels, True),
                ("share", main, False),
            ]
        )
        return ShareLayout(pixels, tuple(segments))

    if role == "right" and inner_bits:
        inner_pixels = np.asarray(inner_bits, dtype=np.uint8)
        if inner_pixels.size % 2 or main.shape[1] % 2:
            raise ValueError("Share destra e pointer non sono divisibili in due metà.")
        pointer_half = inner_pixels.size // 2
        image_half = main.shape[1] // 2
        pixels = compose(
            [
                ("pointer metà sinistra", inner_pixels[:pointer_half], True),
                ("share metà sinistra", main[:, :image_half], False),
                ("pointer metà destra", inner_pixels[pointer_half:], True),
                ("share metà destra", main[:, image_half:], False),
            ]
        )
        return ShareLayout(pixels, tuple(segments), split_at=pointer_half + image_half)

    return ShareLayout(main.copy(), (PrintableSegment("share", 0, main.shape[1]),))


def layout_to_pil(layout: ShareLayout, *, scale: int = 8) -> Image.Image:
    image = image_to_pil(layout.pixels, scale=scale).convert("RGB")
    draw = ImageDraw.Draw(image)
    height = layout.pixels.shape[0]
    line_width = max(1, scale // 20)
    grid_color = (80, 80, 80)

    for segment in layout.segments:
        start = segment.start * scale
        end = (segment.start + segment.width) * scale
        is_pointer = "pointer" in segment.label
        top_row = height - 1 if is_pointer else 0
        bottom_row = height

        for column in range(segment.width + 1):
            x = min(image.width - 1, start + column * scale)
            draw.line(
                (x, top_row * scale, x, bottom_row * scale - 1),
                fill=grid_color,
                width=line_width,
            )
        for row in range(top_row, bottom_row + 1):
            y = min(image.height - 1, row * scale)
            draw.line(
                (start, y, min(image.width - 1, end), y),
                fill=grid_color,
                width=line_width,
            )
    return image


def share_to_pil(
    main: BinaryImage,
    role: str,
    pointer_value: BinaryImage,
    *,
    scale: int = 8,
) -> Image.Image:
    """Esporta la share con i blocchi pointer 1×2 anteposti."""
    return layout_to_pil(share_layout(main, role, pointer_value), scale=scale)


def _export_steps(evaluation: Evaluation, folder: Path, scale: int) -> None:
    image_to_pil(evaluation.output_image, scale=scale).save(folder / "output.png")
    for step in evaluation.steps:
        image_to_pil(step.image, scale=scale).save(
            folder / f"step_{step.index:02d}_{step.operation.lower()}.png"
        )


def export_leaf_alternatives(
    construction: Construction,
    destination: str | Path,
    *,
    scale: int = 8,
) -> None:
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    for leaf in construction.leaves:
        for value in (0, 1):
            share_to_pil(
                leaf.images[value], leaf.role, leaf.pointer_values[value], scale=scale
            ).save(
                folder / f"{leaf.occurrence:02d}_{leaf.variable}_value_{value}_share.png"
            )


def export_transferred_shares(
    transfer: Transfer,
    destination: str | Path,
    *,
    scale: int = 8,
) -> None:
    """Esporta esclusivamente le share presenti nel pacchetto trasferito."""
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    for leaf in transfer.leaves:
        share_to_pil(leaf.image, leaf.role, leaf.pointer_value, scale=scale).save(
            folder / f"{leaf.occurrence:02d}_{leaf.variable}_share.png"
        )


def export_reconstruction(
    transfer: Transfer,
    evaluation: Evaluation,
    destination: str | Path,
    *,
    scale: int = 8,
) -> None:
    """Esporta le share ricevute, i passaggi e l'uscita ricostruita."""
    folder = Path(destination)
    export_transferred_shares(transfer, folder, scale=scale)
    _export_steps(evaluation, folder, scale)
