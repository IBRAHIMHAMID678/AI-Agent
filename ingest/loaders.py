"""File loaders: PDF / TXT / Markdown -> {title, text}."""
from pathlib import Path


def load_file(path):
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return {"title": p.stem, "text": text}
    if suffix in (".txt", ".md", ".markdown"):
        return {"title": p.stem, "text": p.read_text(encoding="utf-8", errors="ignore")}
    raise ValueError(f"Unsupported file type: {suffix}")


def load_upload(file_storage, dest_dir):
    """Persist an uploaded file object (has .filename and .file) and load it."""
    dest = Path(dest_dir) / Path(file_storage.filename).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(file_storage.file.read())
    return load_file(dest)
