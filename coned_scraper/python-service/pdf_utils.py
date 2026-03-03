"""
Shared PDF download and store logic.
Used by both the API (manual download) and the scraper (auto-download).
"""
import os

import db
from data_config import DATA_DIR


async def download_and_store_pdf(pdf_url: str, bill_id: int) -> dict:
    """
    Download PDF from URL and store for bill_id.
    Saves to bills/bill_{id}.pdf, upserts BillDocument, parses and upserts BillDetails.
    Returns {success, message, size_bytes}.
    Raises Exception on failure (e.g. bill not found, download failed).
    """
    import aiohttp

    if not (
        "blob.core.windows.net" in pdf_url
        or ".pdf" in pdf_url.lower()
        or "cecony" in pdf_url.lower()
    ):
        await db.add_log("warning", f"URL doesn't look like a ConEd PDF: {pdf_url[:50]}...")

    bill = await db.get_bill_by_id(bill_id) if bill_id else None
    if bill_id and not bill:
        raise ValueError(f"Bill not found: {bill_id}")

    async with aiohttp.ClientSession() as session:
        async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status != 200:
                await db.add_log("error", f"PDF download failed: HTTP {response.status}")
                raise ValueError(f"Failed to download: HTTP {response.status}")
            pdf_content = await response.read()
            if len(pdf_content) < 1000:
                raise ValueError("Downloaded file too small to be valid PDF")

    bills_dir = DATA_DIR / "bills"
    bills_dir.mkdir(exist_ok=True)
    pdf_path = bills_dir / f"bill_{bill_id}.pdf"
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)
    await db.upsert_bill_document(bill_id, f"bills/bill_{bill_id}.pdf", source_url=pdf_url)
    size_kb = round(len(pdf_content) / 1024, 1)
    await db.add_log("success", f"PDF saved for bill {bill_id}: {size_kb} KB")

    try:
        from pdf_parser import parse_coned_bill_pdf

        parsed_data = parse_coned_bill_pdf(str(pdf_path))
        if "error" not in parsed_data:
            await db.upsert_bill_details(bill_id, **parsed_data)
            await db.add_log(
                "info",
                f"Parsed bill details: kWh={parsed_data.get('kwh_used')}, due={parsed_data.get('due_date')}",
            )
        else:
            await db.add_log("warning", f"PDF parsing error: {parsed_data.get('error')}")
    except Exception as parse_e:
        await db.add_log("warning", f"Failed to parse PDF: {parse_e}")

    return {
        "success": True,
        "message": f"PDF saved ({size_kb} KB)",
        "size_bytes": len(pdf_content),
    }
