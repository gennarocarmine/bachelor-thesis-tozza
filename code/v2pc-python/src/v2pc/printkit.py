"""Kit di stampa per l'esperimento fisico con trasparenze."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
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
CARDS_PER_PAGE = 3
CONTENT_TOP = 390
CONTENT_BOTTOM = 3290
CARD_GAP = 42
CUT_PADDING = 34
LABEL_GAP = 48
REGISTRATION_RADIUS = 18
TEXT_MARK_GAP = 24
LABEL_MAX_WIDTH = 320
LABEL_MIN_FONT = 28
LABEL_MAX_FONT = 40

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
    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Compatibility with Pillow 10.0's bitmap fallback.
        return ImageFont.load_default()


def _registration_mark(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    radius = REGISTRATION_RADIUS
    draw.line((x - radius, y, x + radius, y), fill="black", width=3)
    draw.line((x, y - radius, x, y + radius), fill="black", width=3)
    draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline="black", width=2)


@dataclass(frozen=True)
class _PrintItem:
    title: str
    subtitle: str
    png_path: str
    layout: ShareLayout
    input_label: str | None = None


def _label_reserve(items: list[_PrintItem]) -> int:
    """Reserve room outside the cutting border; keep one scale per kit."""
    font = _font(LABEL_MAX_FONT)
    widths = [
        font.getbbox(item.input_label)[2] - font.getbbox(item.input_label)[0]
        for item in items if item.input_label
    ]
    return min(LABEL_MAX_WIDTH, max(widths)) + LABEL_GAP if widths else 0


def _draw_input_label(draw, label: str, *, box: tuple, height: int) -> None:
    size = max(LABEL_MIN_FONT, min(LABEL_MAX_FONT, round(height * 0.12)))
    font = _font(size)
    # Wrap unusually long variable names instead of shrinking them illegibly.
    lines = []
    line = ""
    for char in label:
        if line and draw.textlength(line + char, font=font) > LABEL_MAX_WIDTH:
            lines.append(line)
            line = ""
        line += char
    lines.append(line)
    text = "\n".join(lines)
    bounds = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
    width, text_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    if text_height > height + 2 * CUT_PADDING:
        raise ValueError("Nome di variabile troppo lungo per l'etichetta A4.")
    draw.multiline_text(
        (box[0] - LABEL_GAP - width - bounds[0],
         (box[1] + box[3] - text_height) // 2 - bounds[1]),
        text, fill="black", font=font, spacing=4, align="right",
    )


def _print_scale(items: list[_PrintItem]) -> int:
    if not items:
        raise ValueError("Non ci sono share da inserire nel kit di stampa.")
    max_width = max(item.layout.pixels.shape[1] for item in items)
    max_height = max(item.layout.pixels.shape[0] for item in items)
    available_width = PAGE_WIDTH - 2 * (PAGE_MARGIN + CUT_PADDING) - _label_reserve(items)
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
    label_reserve = _label_reserve(items)
    chunks = [
        items[start : start + CARDS_PER_PAGE]
        for start in range(0, len(items), CARDS_PER_PAGE)
    ]

    for page_index, page_items in enumerate(chunks):
        content_top = CONTENT_TOP if page_index == 0 else PAGE_MARGIN
        row_height = (
            CONTENT_BOTTOM
            - content_top
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

        # Intestazione e istruzioni una sola volta; scala e pagina restano
        # nel piè di pagina di ogni foglio, anche se stampato separatamente.
        if page_index == 0:
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
            top = content_top + row * (row_height + CARD_GAP)
            strip = layout_to_pil(item.layout, scale=scale)
            x = (PAGE_WIDTH - strip.width - label_reserve) // 2 + label_reserve
            detail_bottom = draw.textbbox(
                (PAGE_MARGIN, top + 50), item.subtitle, font=card_detail_font
            )[3]
            y = max(top + 155, detail_bottom + TEXT_MARK_GAP
                    + REGISTRATION_RADIUS + CUT_PADDING)

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
            if item.input_label:
                _draw_input_label(draw, item.input_label, box=box, height=strip.height)
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
                        box[3] + REGISTRATION_RADIUS + TEXT_MARK_GAP,
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
    readme_en: str,
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
        bundle.writestr(
            "LEGGIMI.txt",
            "ISTRUZIONI / INSTRUCTIONS\n"
            "Italiano: prima sezione. English: second section below.\n\n"
            "=== ITALIANO ===\n\n"
            + readme.rstrip()
            + "\n\n=== ENGLISH ===\n\n"
            + readme_en.rstrip()
            + "\n",
        )
    archive.seek(0)
    return archive


def build_print_kit(
    transfer: Transfer,
    evaluation: Evaluation,
    *,
    assignment: Mapping[str, int] | None = None,
) -> BytesIO:
    """Restituisce uno ZIP con PDF A4 e PNG delle share selezionate."""
    # Optional display metadata: reconstruction still receives only Transfer.
    if assignment is not None:
        for leaf in transfer.leaves:
            if leaf.variable not in assignment or assignment[leaf.variable] not in (0, 1):
                raise ValueError(f"Valore 0/1 mancante o non valido per {leaf.variable}.")
    items = [
        _PrintItem(
            title=f"S{index:02d} - {leaf.variable}",
            subtitle=distribution_label(leaf.party, leaf.delivery),
            png_path=(
                f"share_png/{_DISTRIBUTION_FOLDERS[leaf.delivery]}/"
                f"{index:02d}_{leaf.variable}.png"
            ),
            layout=share_layout(leaf.image, leaf.role, leaf.pointer_value),
            input_label=(
                f"{leaf.variable} = {int(assignment[leaf.variable])}"
                if assignment is not None else None
            ),
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
    assembly_steps_en = [
        f"{step.output_name} ({step.operation}): overlay {step.left_source} "
        f"with the {step.selected_half} half of {step.right_source}; "
        f"pointer={step.pointer}; readout={step.decoded_value}."
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
            + (
                "ETICHETTE DEL KIT DIMOSTRATIVO\n"
                "Accanto a ogni share nel PDF sono indicati variabile e valore "
                "selezionato. Le etichette sono fuori dal bordo di taglio: "
                "non coprono immagini o pointer e vanno escluse dal ritaglio. "
                "Il foglio etichettato espone gli input ed e destinato alla "
                "verifica didattica dopo la selezione, non alla distribuzione "
                "riservata tramite OT. I PNG contengono soltanto le share.\n\n"
                if assignment is not None else ""
            )
            +
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
        readme_en=(
            "V2PC PRINT KIT\n\n"
            "CONTENTS\n"
            "- v2pc_share_selezionate_A4.pdf: print-ready sheets.\n"
            "- share_png/: digital copies of the received shares.\n"
            "- riferimento_uscita.png: reference image obtained at the end "
            "of reconstruction.\n\n"
            "PRINTING AND CUTTING\n"
            "1. Print the PDF on transparent sheets at 100% / actual size.\n"
            "2. Disable any 'Fit to page' option.\n"
            "3. Use the registration marks for cutting and alignment.\n"
            "4. Each pointer is a 1 x 2 block prepended to the share, "
            "following Scheme-(2,2)-NS in the paper.\n"
            "5. In concatenated right shares, each pointer precedes its "
            "own half: left pointer, left image, right pointer, right image.\n"
            "6. The thin grid shows individual logical pixels, as in the "
            "final plates of the paper.\n"
            "7. PNG files are digital copies at the same common scale.\n\n"
            + (
                "DEMONSTRATION KIT LABELS\n"
                "Each share in the PDF has its variable and selected value "
                "printed alongside it. Labels are outside the cutting border: "
                "they do not cover images or pointers and must be excluded "
                "from the cutout. The labelled sheet reveals the inputs and "
                "is intended for educational verification after selection, "
                "not private distribution through OT. PNG files contain "
                "only the shares.\n\n"
                if assignment is not None else ""
            )
            +
            "DISTRIBUTION\n"
            "Alice's x shares are marked for direct delivery. "
            "Bob's y shares have already been selected through simulated "
            "OT: this archive does not implement physical or network "
            "oblivious transfer.\n\n"
            "CUTTING AND OVERLAYING\n"
            "Input shares are identified as S01, S02, ... in the same "
            "order as in the PDF. Gates follow the tree numbering used in "
            "the paper and the C++ implementation: G1, G2, G3, G6, G7, ...\n"
            "At each step, read the clear pointer on the left share to "
            "choose a half of the right share. Each right half is a "
            "self-contained group consisting of its pointer followed by "
            "its image. Cut along the central guide and keep the selected "
            "group. Overlay the selected image with the left share, and "
            "overlay the selected pointer share with the shares of the "
            "pointer bits needed by subsequent gates.\n\n"
            "SEQUENCE FOR THIS CIRCUIT\n"
            + "\n".join(assembly_steps_en)
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
    channels_en = {
        PARTY_ALICE: (
            "Alice: after choosing her input bit, directly deliver the "
            "corresponding share"
        ),
        PARTY_BOB: "Bob: prepare the pair for physical oblivious transfer",
    }
    distribution_rows_en = [
        f"S{index:02d} {leaf.variable}: "
        + channels_en.get(
            leaf.party,
            "Unassigned party: the delivery channel must be explicitly chosen",
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
        readme_en=(
            "V2PC CONSTRUCTION - ALL ALTERNATIVES\n\n"
            "CONTENTS\n"
            "- v2pc_tutte_le_alternative_A4.pdf: all alternatives "
            "at the same printing scale.\n"
            "- alternative/: individual PNG files, two per input "
            "occurrence.\n\n"
            "CONSTRUCTION AND PRINTING\n"
            "This folder contains two shares for each input occurrence: "
            "one for value 0 and one for value 1.\n"
            "The construction was generated without using input values.\n"
            "The A4 PDF contains all alternatives at a common physical "
            "scale, with registration marks and cutting borders.\n"
            "The thin grid shows individual logical pixels, as in the "
            "final plates of the paper.\n"
            "Each image includes 1 x 2 pointer blocks prepended to the share.\n"
            "In right shares, each pointer is placed immediately before "
            "the half it belongs to, as in the paper's figures.\n"
            "For x inputs, Alice selects her alternative and delivers it "
            "directly. For y inputs, Bob must receive the corresponding "
            "alternative through oblivious transfer.\n"
            "Print the PDF at 100% / actual size, disable 'Fit to page', "
            "and use the registration marks for cutting and alignment.\n\n"
            "SHARE DISTRIBUTION PLAN\n"
            "Demo convention: x = Alice's input, y = Bob's input.\n"
            "Each occurrence is a distinct wire, even when a variable "
            "name is repeated.\n\n"
            + "\n".join(distribution_rows_en)
            + "\n\n"
            "PREPARING PHYSICAL DISTRIBUTION\n"
            "This archive contains all alternatives and is produced "
            "before input values are known.\n\n"
            "ALICE'S INPUTS (x)\n"
            "For each of her input occurrences, Alice chooses the "
            "value_0 or value_1 file and delivers it directly to Bob.\n\n"
            "BOB'S INPUTS (y)\n"
            "For each occurrence, prepare both alternatives, value_0 "
            "and value_1, and apply the physical oblivious transfer "
            "described in the paper, so that Bob obtains only the share "
            "for his bit without revealing his choice to Alice.\n"
            "In the PDF, values 0 and 1 are printed only outside the "
            "cutting border: labels must not remain on the delivered "
            "transparency, and the two envelopes must be indistinguishable.\n"
            "The two alternatives must remain indistinguishable from "
            "the outside, and Alice must not observe the choice. "
            "The alternative not received must not enter reconstruction.\n\n"
            "LIMITATIONS\n"
            "These instructions organize the materials but do not by "
            "themselves provide OT security guarantees: the physical "
            "experiment must follow the complete procedure and threat "
            "model in the paper. The web demo and CLI only perform a "
            "locally simulated selection.\n"
        ),
    )
