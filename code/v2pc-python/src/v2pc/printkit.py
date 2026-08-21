"""Kit di stampa per l'esperimento fisico con trasparenze."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw, ImageFont

from .protocol import (
    DELIVERY_DIRECT,
    DELIVERY_SIMULATED_OT,
    Construction,
    Evaluation,
    PARTY_ALICE,
    PARTY_BOB,
    Transfer,
    distribution_label,
)
from .render import ShareLayout, image_to_pil, layout_to_pil, share_layout

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

_DISTRIBUTION_FOLDERS = {
    DELIVERY_DIRECT: "alice_consegna_diretta",
    DELIVERY_SIMULATED_OT: "bob_ot_simulato",
    "simulated_selection": "parte_non_assegnata",
}
_CONSTRUCTION_SUBTITLES = {
    PARTY_ALICE: "Alice - selezione e consegna diretta",
    PARTY_BOB: "Bob - coppia da predisporre per l'OT fisico",
}
_CONSTRUCTION_CHANNELS = {
    PARTY_ALICE: (
        "Alice: dopo aver scelto il proprio bit, consegna direttamente "
        "la share corrispondente"
    ),
    PARTY_BOB: "Bob: predisporre la coppia per l'oblivious transfer fisico",
}


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
    png_path: str
    layout: ShareLayout


def _print_scale(items: list[_PrintItem]) -> int:
    if not items:
        raise ValueError("Non ci sono share da inserire nel kit di stampa.")
    max_width = max(item.layout.pixels.shape[1] for item in items)
    max_height = max(item.layout.pixels.shape[0] for item in items)
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


def _print_pages(
    items: list[_PrintItem],
    *,
    scale: int,
    heading: str,
    subheading: str,
) -> list[Image.Image]:
    pages: list[Image.Image] = []
    chunks = [
        items[start : start + CARDS_PER_PAGE]
        for start in range(0, len(items), CARDS_PER_PAGE)
    ]

    for page_index, page_items in enumerate(chunks):
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
            strip = layout_to_pil(item.layout, scale=scale)
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

            if item.layout.split_at is not None:
                guide_x = x + item.layout.split_at * scale
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
        draw.text(
            (PAGE_MARGIN, PAGE_HEIGHT - 120),
            f"Scala comune: 1 pixel del protocollo = {cell_mm:.2f} mm "
            f"({scale} pixel a {PRINT_DPI} dpi) - pagina {page_index + 1}",
            fill="black",
            font=footer_font,
        )
        pages.append(page)
    return pages


def _png_bytes(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG", dpi=(PRINT_DPI, PRINT_DPI))
    return stream.getvalue()


def _build_kit(
    items: list[_PrintItem],
    *,
    scale: int,
    pdf_name: str,
    heading: str,
    subheading: str,
    readme: str,
    extra: tuple[tuple[str, bytes], ...] = (),
) -> BytesIO:
    pages = _print_pages(items, scale=scale, heading=heading, subheading=subheading)
    pdf = BytesIO()
    pages[0].save(
        pdf,
        format="PDF",
        resolution=PRINT_DPI,
        save_all=True,
        append_images=pages[1:],
    )

    archive = BytesIO()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr(pdf_name, pdf.getvalue())
        for item in items:
            bundle.writestr(item.png_path, _png_bytes(layout_to_pil(item.layout, scale=scale)))
        for name, data in extra:
            bundle.writestr(name, data)
        bundle.writestr("LEGGIMI.txt", readme)
    archive.seek(0)
    return archive


def build_print_kit(transfer: Transfer, evaluation: Evaluation) -> BytesIO:
    """Restituisce uno ZIP con PDF A4 e PNG delle share selezionate."""
    items = [
        _PrintItem(
            title=f"S{index:02d} - {leaf.variable}",
            subtitle=distribution_label(leaf.party, leaf.delivery),
            png_path=(
                f"share_png/{_DISTRIBUTION_FOLDERS[leaf.delivery]}/"
                f"{index:02d}_{leaf.variable}.png"
            ),
            layout=share_layout(leaf.image, leaf.role, leaf.pointer_value),
        )
        for index, leaf in enumerate(transfer.leaves, start=1)
    ]
    scale = _print_scale(items)

    assembly_steps = [
        f"{step.output_name} ({step.operation}): sovrapporre {step.left_source} "
        f"alla meta {'sinistra' if step.selected_half == 'left' else 'destra'} "
        f"di {step.right_source}; pointer={step.pointer}; "
        f"lettura={step.decoded_value}."
        for step in evaluation.steps
    ]
    output_png = _png_bytes(
        image_to_pil(evaluation.output_image, scale=scale).convert("RGB")
    )

    return _build_kit(
        items,
        scale=scale,
        pdf_name="v2pc_share_selezionate_A4.pdf",
        heading="V2PC - share selezionate",
        subheading=(
            "Kit di verifica dopo la selezione degli input; "
            "le alternative scartate non sono incluse."
        ),
        extra=(("riferimento_uscita.png", output_png),),
        readme=(
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


def build_construction_kit(construction: Construction) -> BytesIO:
    """ZIP con entrambe le alternative per ogni occorrenza di input."""
    items = [
        _PrintItem(
            title=f"S{index:02d} - {leaf.variable} - alternativa {value}",
            subtitle=_CONSTRUCTION_SUBTITLES.get(
                leaf.party, "Parte non assegnata - selezione locale"
            ),
            png_path=f"alternative/{index:02d}_{leaf.variable}_value_{value}.png",
            layout=share_layout(
                leaf.images[value], leaf.role, leaf.pointer_values[value]
            ),
        )
        for index, leaf in enumerate(construction.leaves, start=1)
        for value in (0, 1)
    ]
    distribution_rows = [
        f"S{index:02d} {leaf.variable}: "
        + _CONSTRUCTION_CHANNELS.get(
            leaf.party,
            "Parte non assegnata: il canale deve essere deciso esplicitamente",
        )
        + "."
        for index, leaf in enumerate(construction.leaves, start=1)
    ]

    return _build_kit(
        items,
        scale=_print_scale(items),
        pdf_name="v2pc_tutte_le_alternative_A4.pdf",
        heading="V2PC - tutte le alternative",
        subheading=(
            "Materiale preparato prima di conoscere gli input: "
            "due alternative per ogni occorrenza."
        ),
        readme=(
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
