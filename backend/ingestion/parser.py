from dataclasses import dataclass
from pathlib import Path

from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import (
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)


@dataclass
class Chunk:
    content: str
    section: str | None
    page: int | None
    is_table: bool
    is_figure: bool
    chunk_index: int


# CPU-only: MPS (Apple Silicon GPU) doesn't support float64 which DocLing's
# RT-DETR layout model requires. No OCR and no TableFormer (re-enable in Phase 3).
_pipeline_opts = PdfPipelineOptions(
    do_ocr=False,
    do_table_structure=False,
    accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU),
)
_converter = DocumentConverter(
    format_options={"pdf": PdfFormatOption(pipeline_options=_pipeline_opts)}
)


def _page(item) -> int | None:
    return item.prov[0].page_no if item.prov else None


def parse_pdf(pdf_path: Path) -> tuple[str, list[Chunk]]:
    """Parse PDF and return (paper_title, chunks).

    Returns the document title from DocLing metadata and the list of chunks.
    """
    result = _converter.convert(str(pdf_path))
    doc = result.document

    # Extract paper title from document metadata
    paper_title = "Unknown Paper"
    if hasattr(doc, 'name') and doc.name:
        paper_title = doc.name.strip()
    elif hasattr(doc, 'title') and doc.title:
        paper_title = doc.title.strip()

    chunks: list[Chunk] = []
    current_section: str | None = None
    chunk_index = 0

    for item, _level in doc.iterate_items():
        if isinstance(item, SectionHeaderItem):
            current_section = item.text.strip() or current_section
            continue

        if isinstance(item, TableItem):
            content = item.export_to_markdown().strip()
            if not content:
                continue
            chunks.append(
                Chunk(
                    content=content,
                    section=current_section,
                    page=_page(item),
                    is_table=True,
                    is_figure=False,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

        elif isinstance(item, PictureItem):
            caption = item.caption_text(doc).strip()
            if not caption:
                continue
            chunks.append(
                Chunk(
                    content=caption,
                    section=current_section,
                    page=_page(item),
                    is_table=False,
                    is_figure=True,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

        elif isinstance(item, TextItem):
            content = item.text.strip()
            if not content:
                continue
            chunks.append(
                Chunk(
                    content=content,
                    section=current_section,
                    page=_page(item),
                    is_table=False,
                    is_figure=False,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return paper_title, chunks
