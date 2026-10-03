"""Clean a SunGrid document, then split it into one chunk per section.
Cleaning runs first: line endings, bold markers, and case. Chunking then
splits on `##` headings. A markdown table stays inside its section and is
rewritten as one sentence per row so the header stays attached to the cell.
"""

from pathlib import Path
from app.config import root_dir

DOCUMENT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "01_program_policies.md": ("Program Policies",),
    "02_incentive_rebate_programs.md": ("Incentive & Rebate Programs",),
    "03_billing_faqs.md": ("Billing & Account",),
    "04_technical_installation_guidance.md": ("Technical/Installation Guidance",),
    "05_company_updates.md": ("Company Updates",),
    "06_ambiguous_rebate_billing_adjustments.md": (
        "Incentive & Rebate Programs",
        "Billing & Account",
    ),
    "07_installer_certification.md": (
        "Program Policies",
        "Incentive & Rebate Programs",
    ),
    "08_governance_voting.md": ("Program Policies",),
    "09_battery_storage_incentive.md": ("Incentive & Rebate Programs",),
    "10_low_income_bill_credit.md": ("Incentive & Rebate Programs",),
    "11_net_metering_trueup.md": ("Billing & Account",),
    "12_autopay_failure_policy.md": ("Billing & Account",),
    "13_battery_storage_installation.md": ("Technical/Installation Guidance",),
    "14_annual_impact_report.md": ("Company Updates",),
}


def docs_dir() -> Path:
    """Folder of starter-kit markdown files."""
    return root_dir() / "SunGrid Starter Kit" / "docs"


def clean_text(raw: str) -> str:
    """Normalize endings, drop bold markers, and lowercase."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("**", "")
    lines = [line.rstrip() for line in text.lower().split("\n")]
    return "\n".join(lines).strip()


def chunk_markdown(source: str, raw: str) -> list[dict[str, str | list[str]]]:
    """Return cleaned section chunks for one document."""
    if source not in DOCUMENT_CATEGORIES:
        raise KeyError(f"No categories configured for {source}.")
    categories = list(DOCUMENT_CATEGORIES[source])
    prefix = source[:2]
    chunks: list[dict[str, str | list[str]]] = []
    for index, (title, heading, body) in enumerate(split_sections(clean_text(raw))):
        chunks.append(
            {
                "id": f"{prefix}#{index}",
                "source": source,
                "section": section_label(title, heading),
                "text": chunk_body(heading, body),
                "section_categories": list(categories),
                "chunk_categories": list(categories),
            }
        )
    return chunks


def load_chunks(folder: Path | None = None) -> list[dict[str, str | list[str]]]:
    """Chunk every markdown file in the starter kit, in filename order."""
    chunks: list[dict[str, str | list[str]]] = []
    for path in sorted((folder or docs_dir()).glob("*.md")):
        chunks.extend(chunk_markdown(path.name, path.read_text(encoding="utf-8")))
    return chunks


def split_sections(text: str) -> list[tuple[str, str, str]]:
    """Split cleaned markdown into (title, heading, body) tuples.

    Text above the first `##` heading is kept as its own chunk. The title
    comes from the single leading `#` line.
    """
    lines = text.split("\n")
    title = ""
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]

    sections: list[tuple[str, str, str]] = []
    heading = ""
    body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            append_section(sections, title, heading, body)
            heading = line[3:].strip()
            body = []
            continue
        body.append(line)
    append_section(sections, title, heading, body)
    return sections


def append_section(sections: list[tuple[str, str, str]], title: str,
                   heading: str, body_lines: list[str]) -> None:
    """Keep a section that has a heading or some body text."""
    body = "\n".join(body_lines).strip()
    if heading or body:
        sections.append((title, heading, body))


def section_label(title: str, heading: str) -> str:
    """Join the document title and the section heading for display."""
    if heading:
        return f"{title} > {heading}"
    return title


def chunk_body(heading: str, body: str) -> str:
    """Section text, with any markdown table written as sentences."""
    rewritten = rewrite_tables(body)
    if heading:
        return f"{heading}\n{rewritten}".strip()
    return rewritten


def rewrite_tables(text: str) -> str:
    """Replace each markdown table with one sentence per data row."""
    lines = text.split("\n")
    output: list[str] = []
    index = 0
    while index < len(lines):
        if is_table_row(lines[index]):
            block: list[str] = []
            while index < len(lines) and is_table_row(lines[index]):
                block.append(lines[index])
                index += 1
            output.append(table_to_sentences(block))
            continue
        output.append(lines[index])
        index += 1
    return "\n".join(output).strip()


def is_table_row(line: str) -> bool:
    """A markdown table row starts and ends with a pipe."""
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def table_to_sentences(block: list[str]) -> str:
    """Turn header plus rows into 'cell: header value, ...' sentences."""
    rows = [cells(line) for line in block if not is_separator_row(line)]
    if len(rows) < 2:
        return " ".join(line.strip() for line in block)
    headers = rows[0]
    sentences: list[str] = []
    for row in rows[1:]:
        pairs = [
            f"{header} {value}"
            for header, value in zip(headers[1:], row[1:])
            if header and value
        ]
        if row and row[0] and pairs:
            sentences.append(f"{row[0]}: {', '.join(pairs)}.")
    return " ".join(sentences)


def cells(line: str) -> list[str]:
    """Split one table row into stripped cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(line: str) -> bool:
    """The `|---|` row under a markdown header."""
    parsed = cells(line)
    if not parsed:
        return False
    return all(cell and set(cell) <= set("-: ") for cell in parsed)
