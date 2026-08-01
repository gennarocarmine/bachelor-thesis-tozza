"""Kit di stampa per l'esperimento fisico con trasparenze."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .protocol import (
    DELIVERY_DIRECT,
    DELIVERY_SIMULATED_OT,
    Construction,
    Evaluation,
    Transfer,
)
from .render import (
    PrintableSegment,
    image_to_pil,
    printable_layout_to_pil,
    printable_share_layout,
    printable_transferred_share_layout,
)

PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508
PAGE_MARGIN = 180
PRINT_DPI = 300
MAX_PRINT_SCALE = 64
MAX_SHARE_HEIGHT = 480
CARDS_PER_PAGE = 4
CONTENT_TOP = 390
CONTENT_BOTTOM = 3290
CARD_GAP = 42
CUT_PADDING = 34


def _distribution_label(delivery: str) -> str:
    return {
        DELIVERY_DIRECT: "Alice — consegna diretta",
        DELIVERY_SIMULATED_OT: "Bob — OT simulato",
        "simulated_selection": "parte non assegnata — selezione locale",
    }[delivery]


def _distribution_folder(delivery: str) -> str:
    return {
        DELIVERY_DIRECT: "alice_consegna_diretta",
        DELIVERY_SIMULATED_OT: "bob_ot_simulato",
        "simulated_selection": "parte_non_assegnata",
    }[delivery]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def _registration_mark(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    radius = 18
    draw.line((x - radius, y, x + radius, y), fill="black", width=3)
    draw.line((x, y - radius, x, y + radius), fill="black", width=3)
    draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline="black", width=2)


@dataclass(frozen=True)
class _PrintItem:
    title: str
    subtitle: str
    layout: np.ndarray
    segments: tuple[PrintableSegment, ...]
    role: str


def _print_scale(items: list[_PrintItem]) -> int:
    if not items:
        raise ValueError("Non ci sono share da inserire nel kit di stampa.")
    max_width = max(item.layout.shape[1] for item in items)
    max_height = max(item.layout.shape[0] for item in items)
    available_width = PAGE_WIDTH - 2 * (PAGE_MARGIN + CUT_PADDING)
    if max_width > available_width or max_height > MAX_SHARE_HEIGHT:
        raise ValueError(
            "Le share sono troppo larghe per un foglio A4 anche alla scala minima; "
            "ridurre il lato dell'immagine o la profondità della formula."
        )
    return max(
        1,
        min(
            MAX_PRINT_SCALE,
            available_width // max_width,
            MAX_SHARE_HEIGHT // max_height,
        ),
    )


def _right_half_boundary(item: _PrintItem) -> int | None:
    labels = [segment.label for segment in item.segments]
    if item.role != "right" or labels != [
        "pointer metà sinistra",
        "share metà sinistra",
        "pointer metà destra",
        "share metà destra",
    ]:
        return None
    return item.segments[2].start


def _print_pages(
    items: list[_PrintItem],
    *,
    scale: int,
    heading: str,
    subheading: str,
) -> list[Image.Image]:
    pages: list[Image.Image] = []
    page_count = (len(items) + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
    base_size, extra = divmod(len(items), page_count)
    page_start = 0

    for page_index in range(page_count):
        page_size = base_size + (1 if page_index < extra else 0)
        page_items = items[page_start : page_start + page_size]
        page_start += page_size
        row_height = (
            CONTENT_BOTTOM
            - CONTENT_TOP
            - CARD_GAP * (len(page_items) - 1)
        ) // len(page_items)
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
        draw = ImageDraw.Draw(page)
        title_font = _font(62, bold=True)
        subtitle_font = _font(31)
        card_font = _font(39, bold=True)
        card_detail_font = _font(27)
        guide_font = _font(24, bold=True)
        footer_font = _font(27)

        draw.text((PAGE_MARGIN, 100), heading, fill="black", font=title_font)
        draw.text((PAGE_MARGIN, 185), subheading, fill="black", font=subtitle_font)
        draw.text(
            (PAGE_MARGIN, 235),
            "Stampare al 100% / dimensioni reali. Disattivare 'Adatta alla pagina'.",
            fill="black",
            font=subtitle_font,
        )
        draw.line(
            (PAGE_MARGIN, 310, PAGE_WIDTH - PAGE_MARGIN, 310),
            fill=(130, 130, 130),
            width=2,
        )

        for row, item in enumerate(page_items):
            top = CONTENT_TOP + row * (row_height + CARD_GAP)
            strip = printable_layout_to_pil(
                item.layout,
                item.segments,
                scale=scale,
            )
            x = (PAGE_WIDTH - strip.width) // 2
            y = top + 105

            draw.text((PAGE_MARGIN, top), item.title, fill="black", font=card_font)
            draw.text(
                (PAGE_MARGIN, top + 50),
                item.subtitle,
                fill=(55, 55, 55),
                font=card_detail_font,
            )
            page.paste(strip, (x, y))

            box = (
                x - CUT_PADDING,
                y - CUT_PADDING,
                x + strip.width + CUT_PADDING,
                y + strip.height + CUT_PADDING,
            )
            draw.rectangle(box, outline=(105, 105, 105), width=2)
            for mark_x, mark_y in (
                (box[0], box[1]),
                (box[2], box[1]),
                (box[0], box[3]),
                (box[2], box[3]),
            ):
                _registration_mark(draw, mark_x, mark_y)

            boundary = _right_half_boundary(item)
            if boundary is not None:
                guide_x = x + boundary * scale
                draw.line(
                    (guide_x, box[1] - 12, guide_x, y - 4),
                    fill=(70, 70, 70),
                    width=3,
                )
                draw.line(
                    (guide_x, y + strip.height + 4, guide_x, box[3] + 12),
                    fill=(70, 70, 70),
                    width=3,
                )
                label = "separazione delle due metà"
                label_box = draw.textbbox((0, 0), label, font=guide_font)
                label_width = label_box[2] - label_box[0]
                draw.text(
                    (
                        max(PAGE_MARGIN, min(
                            guide_x - label_width // 2,
                            PAGE_WIDTH - PAGE_MARGIN - label_width,
                        )),
                        box[3] + 14,
                    ),
                    label,
                    fill=(70, 70, 70),
                    font=guide_font,
                )

        cell_mm = scale * 25.4 / PRINT_DPI
        page_number = page_index + 1
        draw.text(
            (PAGE_MARGIN, PAGE_HEIGHT - 120),
            f"Scala comune: 1 pixel del protocollo = {cell_mm:.2f} mm "
            f"({scale} pixel a {PRINT_DPI} dpi) - pagina {page_number}",
            fill="black",
            font=footer_font,
        )
        pages.append(page)
    return pages


def _pages_to_pdf(pages: list[Image.Image]) -> bytes:
    if not pages:
        raise ValueError("Il kit di stampa non contiene pagine.")
    stream = BytesIO()
    pages[0].save(
        stream,
        format="PDF",
        resolution=PRINT_DPI,
        save_all=True,
        append_images=pages[1:],
    )
    return stream.getvalue()


def _selected_print_items(transfer: Transfer) -> list[_PrintItem]:
    items: list[_PrintItem] = []
    for index, leaf in enumerate(transfer.leaves, start=1):
        layout, segments = printable_transferred_share_layout(leaf)
        items.append(
            _PrintItem(
                title=f"S{index:02d} - {leaf.variable}",
                subtitle=_distribution_label(leaf.delivery),
                layout=layout,
                segments=segments,
                role=leaf.role,
            )
        )
    return items


def _construction_print_items(construction: Construction) -> list[_PrintItem]:
    items: list[_PrintItem] = []
    for index, leaf in enumerate(construction.leaves, start=1):
        if leaf.party == "alice":
            subtitle = "Alice - selezione e consegna diretta"
        elif leaf.party == "bob":
            subtitle = "Bob - coppia da predisporre per l'OT fisico"
        else:
            subtitle = "Parte non assegnata - selezione locale"
        for value in (0, 1):
            layout, segments = printable_share_layout(leaf, value)
            items.append(
                _PrintItem(
                    title=f"S{index:02d} - {leaf.variable} - alternativa {value}",
                    subtitle=subtitle,
                    layout=layout,
                    segments=segments,
                    role=leaf.role,
                )
            )
    return items


def build_print_kit(
    transfer: Transfer,
    evaluation: Evaluation,
) -> BytesIO:
    """Restituisce uno ZIP con PDF A4 e PNG delle share selezionate."""
    items = _selected_print_items(transfer)
    scale = _print_scale(items)
    pdf = _pages_to_pdf(
        _print_pages(
            items,
            scale=scale,
            heading="V2PC - share selezionate",
            subheading=(
                "Kit di verifica dopo la selezione degli input; "
                "le alternative scartate non sono incluse."
            ),
        )
    )

    archive = BytesIO()
    assembly_steps = []
    for step in evaluation.steps:
        selected_half = "sinistra" if step.selected_half == "left" else "destra"
        assembly_steps.append(
            f"{step.output_name} ({step.operation}): sovrapporre {step.left_source} "
            f"alla meta {selected_half} di {step.right_source}; "
            f"pointer={step.pointer}; lettura={step.decoded_value}."
        )

    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("v2pc_share_selezionate_A4.pdf", pdf)
        for index, (leaf, item) in enumerate(
            zip(transfer.leaves, items),
            start=1,
        ):
            image = printable_layout_to_pil(
                item.layout,
                item.segments,
                scale=scale,
            )
            stream = BytesIO()
            image.save(stream, format="PNG", dpi=(PRINT_DPI, PRINT_DPI))
            bundle.writestr(
                f"share_png/{_distribution_folder(leaf.delivery)}/"
                f"{index:02d}_{leaf.variable}.png",
                stream.getvalue(),
            )

        output = BytesIO()
        image_to_pil(evaluation.output_image, scale=scale).convert("RGB").save(
            output, format="PNG", dpi=(PRINT_DPI, PRINT_DPI)
        )
        bundle.writestr("riferimento_uscita.png", output.getvalue())
        bundle.writestr(
            "LEGGIMI.txt",
            (
                "KIT DI STAMPA V2PC\n\n"
                "CONTENUTO\n"
                "- v2pc_share_selezionate_A4.pdf: fogli pronti per la stampa.\n"
                "- share_png/: copie digitali delle share ricevute.\n"
                "- riferimento_uscita.png: immagine attesa al termine della "
                "ricostruzione.\n\n"
                "STAMPA E TAGLIO\n"
                "1. Stampare il PDF su fogli trasparenti al 100% / dimensioni reali.\n"
                "2. Disattivare qualunque opzione 'Adatta alla pagina'.\n"
                "3. Usare i crocini come riferimento per taglio e allineamento.\n"
                "4. Ogni pointer e rappresentato da un blocco 1 x 2 anteposto "
                "alla share, secondo lo Scheme-(2,2)-NS del paper.\n"
                "5. Nelle share destre concatenate ogni pointer precede la "
                "propria meta: pointer sinistro, immagine sinistra, pointer "
                "destro, immagine destra.\n"
                "6. Il reticolo sottile mostra i singoli pixel logici, come "
                "nelle tavole finali del paper.\n"
                "7. I PNG sono forniti come copie digitali alla stessa scala comune.\n\n"
                "DISTRIBUZIONE\n"
                "Le share x di Alice sono indicate come consegna diretta. "
                "La scelta delle share y di Bob e gia avvenuta mediante OT "
                "simulato: questo archivio non esegue un oblivious transfer "
                "fisico o di rete.\n\n"
                "TAGLIO E SOVRAPPOSIZIONE\n"
                "Le share di ingresso sono indicate con S01, S02, ... nello "
                "stesso ordine del PDF. Le porte seguono la numerazione ad "
                "albero del paper e del C++: G1, G2, G3, G6, G7, ...\n"
                "A ogni passo, usare il pointer in chiaro della share sinistra "
                "per scegliere la meta della share destra. Ogni meta destra e "
                "un gruppo autonomo formato dal proprio pointer seguito dalla "
                "relativa immagine. Tagliare lungo la guida centrale e tenere "
                "il gruppo selezionato. Sovrapporre l'immagine scelta alla share "
                "sinistra e la share del pointer scelta alle share dei pointer "
                "bit necessari alle porte successive.\n\n"
                "SEQUENZA PER QUESTO CIRCUITO\n"
                + "\n".join(assembly_steps)
                + "\n"
            ),
        )
    archive.seek(0)
    return archive


def build_construction_kit(
    construction: Construction,
) -> BytesIO:
    """ZIP con entrambe le alternative per ogni occorrenza di input."""
    items = _construction_print_items(construction)
    scale = _print_scale(items)
    pdf = _pages_to_pdf(
        _print_pages(
            items,
            scale=scale,
            heading="V2PC - tutte le alternative",
            subheading=(
                "Materiale preparato prima di conoscere gli input: "
                "due alternative per ogni occorrenza."
            ),
        )
    )
    archive = BytesIO()
    distribution_rows = []
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("v2pc_tutte_le_alternative_A4.pdf", pdf)
        item_index = 0
        for index, leaf in enumerate(construction.leaves, start=1):
            if leaf.party == "alice":
                channel = "Alice: dopo aver scelto il proprio bit, consegna direttamente la share corrispondente"
            elif leaf.party == "bob":
                channel = "Bob: predisporre la coppia per l'oblivious transfer fisico"
            else:
                channel = "Parte non assegnata: il canale deve essere deciso esplicitamente"
            distribution_rows.append(
                f"S{index:02d} {leaf.variable}: {channel}."
            )
            for value in (0, 1):
                item = items[item_index]
                item_index += 1
                image = printable_layout_to_pil(
                    item.layout,
                    item.segments,
                    scale=scale,
                )
                stream = BytesIO()
                image.save(stream, format="PNG", dpi=(PRINT_DPI, PRINT_DPI))
                bundle.writestr(
                    f"alternative/{index:02d}_{leaf.variable}_value_{value}.png",
                    stream.getvalue(),
                )
        bundle.writestr(
            "LEGGIMI.txt",
            (
                "COSTRUZIONE V2PC — TUTTE LE ALTERNATIVE\n\n"
                "CONTENUTO\n"
                "- v2pc_tutte_le_alternative_A4.pdf: tutte le alternative "
                "alla stessa scala di stampa.\n"
                "- alternative/: PNG individuali, due per ogni occorrenza "
                "di input.\n\n"
                "COSTRUZIONE E STAMPA\n"
                "Questa cartella contiene due share per ogni occorrenza di input: "
                "una per il valore 0 e una per il valore 1.\n"
                "La costruzione e stata generata senza usare i valori degli input.\n"
                "Il PDF A4 contiene tutte le alternative a una scala fisica comune, "
                "con crocini e bordi per il taglio.\n"
                "Il reticolo sottile mostra i singoli pixel logici come nelle "
                "tavole finali del paper.\n"
                "Ogni immagine include i blocchi pointer 1 x 2 anteposti alla share.\n"
                "Nelle share destre ogni pointer e collocato immediatamente prima "
                "della meta a cui appartiene, come nelle figure del paper.\n"
                "Per gli ingressi x, Alice seleziona la propria alternativa e la "
                "consegna direttamente. Per gli ingressi y, Bob deve ricevere "
                "l'alternativa corrispondente mediante oblivious transfer.\n"
                "Stampare il PDF al 100% / dimensioni reali, disattivando "
                "l'opzione 'Adatta alla pagina', e usare i crocini per il "
                "taglio e l'allineamento.\n\n"
                "PIANO DI DISTRIBUZIONE DELLE SHARE\n"
                "Convenzione della demo: x = input di Alice, y = input di Bob.\n"
                "Ogni occorrenza e un filo distinto, anche se il nome della "
                "variabile e ripetuto.\n\n"
                + "\n".join(distribution_rows)
                + "\n\n"
                "PREPARAZIONE DELLA DISTRIBUZIONE FISICA\n"
                "Questo archivio contiene tutte le alternative ed e prodotto "
                "prima di conoscere i valori degli input.\n\n"
                "INGRESSI DI ALICE (x)\n"
                "Alice sceglie, per ogni propria occorrenza, il file value_0 "
                "oppure value_1 e lo consegna direttamente a Bob.\n\n"
                "INGRESSI DI BOB (y)\n"
                "Per ogni occorrenza devono essere predisposte entrambe le "
                "alternative value_0 e value_1 e applicato l'oblivious transfer "
                "fisico descritto nel paper, in modo che Bob ottenga soltanto "
                "quella del proprio bit senza rivelare ad Alice quale ha scelto.\n"
                "Nel PDF i valori 0 e 1 sono indicati soltanto fuori dal bordo di "
                "taglio: le etichette non devono restare sulla trasparenza "
                "consegnata e le due buste devono essere indistinguibili.\n"
                "Le due alternative devono restare indistinguibili dall'esterno "
                "e Alice non deve osservare la scelta. L'alternativa non ricevuta "
                "non deve entrare nella ricostruzione.\n\n"
                "LIMITI\n"
                "Queste indicazioni organizzano i materiali ma non realizzano, "
                "da sole, le garanzie di sicurezza dell'OT: per l'esperimento "
                "fisico va seguito integralmente il procedimento e il modello "
                "di minaccia del paper. La demo web e la CLI eseguono invece "
                "soltanto una selezione locale simulata.\n"
            ),
        )
    archive.seek(0)
    return archive
