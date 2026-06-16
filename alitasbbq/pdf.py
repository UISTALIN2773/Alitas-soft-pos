import os


def _pdf_escape_bytes(text):
    if text is None:
        text = ""
    s = str(text)
    b = s.encode("latin-1", "replace")
    b = b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return b


def _wrap_text_lines(text, max_chars):
    if text is None:
        return [""]
    s = str(text).strip()
    if not s:
        return [""]
    words = s.split()
    lines = []
    current = []
    current_len = 0
    for w in words:
        extra = len(w) + (1 if current else 0)
        if current and current_len + extra > max_chars:
            lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += extra
    if current:
        lines.append(" ".join(current))
    return lines


def _mono_text_width_pt(text, font_size):
    return len(str(text)) * float(font_size) * 0.6


def generar_pdf_ticket(file_path, titulo, lineas, subtitulo=None, width_mm=80):
    page_w = int(round((float(width_mm) * 72.0) / 25.4))
    margin_x = 8
    top_margin = 14
    bottom_margin = 14
    leading = 11
    body_size = 9
    title_size = 11
    sub_size = 9

    max_chars = max(10, int((page_w - 2 * margin_x) / (body_size * 0.6)))

    all_lines = []
    if titulo:
        all_lines.append(("center", title_size, str(titulo)))
    if subtitulo:
        all_lines.append(("center", sub_size, str(subtitulo)))
    all_lines.append(("left", body_size, ""))
    for ln in lineas:
        wrapped = _wrap_text_lines(ln, max_chars)
        for w in wrapped:
            all_lines.append(("left", body_size, w))

    max_page_h = 2000
    needed_h = top_margin + bottom_margin + leading * (len(all_lines) + 1)
    page_h = max(200, min(max_page_h, int(needed_h)))
    max_lines = max(1, int((page_h - top_margin - bottom_margin) / leading))

    pages = []
    if len(all_lines) <= max_lines:
        pages = [all_lines]
        page_heights = [page_h]
    else:
        page_h = max_page_h
        max_lines = max(1, int((page_h - top_margin - bottom_margin) / leading))
        page_heights = []
        for i in range(0, len(all_lines), max_lines):
            pages.append(all_lines[i : i + max_lines])
            page_heights.append(page_h)

    offsets = []
    out = bytearray()

    def add_obj(obj_bytes):
        offsets.append(len(out))
        out.extend(obj_bytes)

    out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    font_obj_id = 1
    add_obj(b"1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

    pages_obj_id = 2
    page_ids = []
    content_ids = []
    next_id = 3

    for _ in pages:
        content_ids.append(next_id)
        next_id += 1
        page_ids.append(next_id)
        next_id += 1

    catalog_id = next_id

    for page_idx, page_lines in enumerate(pages):
        ph = page_heights[page_idx]
        content_stream = bytearray()
        content_stream.extend(b"BT\n")

        for i, (align, font_size, txt) in enumerate(page_lines):
            y = float(ph - top_margin - leading * i)
            if align == "center":
                tw = _mono_text_width_pt(txt, font_size)
                x = max(float(margin_x), (float(page_w) - tw) / 2.0)
            else:
                x = float(margin_x)
            content_stream.extend(f"/F1 {int(font_size)} Tf\n".encode("ascii"))
            content_stream.extend(f"1 0 0 1 {x:.2f} {y:.2f} Tm\n".encode("ascii"))
            content_stream.extend(b"(")
            content_stream.extend(_pdf_escape_bytes(txt))
            content_stream.extend(b") Tj\n")

        content_stream.extend(b"ET\n")

        stream_header = f"{content_ids[page_idx]} 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("ascii")
        stream_footer = b"endstream\nendobj\n"
        add_obj(stream_header + content_stream + stream_footer)

        page_obj = (
            f"{page_ids[page_idx]} 0 obj\n"
            f"<< /Type /Page /Parent {pages_obj_id} 0 R /MediaBox [0 0 {page_w} {ph}] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_ids[page_idx]} 0 R >>\nendobj\n"
        ).encode("ascii")
        add_obj(page_obj)

    kids = " ".join([f"{pid} 0 R" for pid in page_ids])
    pages_obj = f"{pages_obj_id} 0 obj\n<< /Type /Pages /Kids [ {kids} ] /Count {len(page_ids)} >>\nendobj\n".encode(
        "ascii"
    )
    add_obj(pages_obj)

    catalog_obj = f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_obj_id} 0 R >>\nendobj\n".encode("ascii")
    add_obj(catalog_obj)

    xref_start = len(out)
    out.extend(f"xref\n0 {catalog_id + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        (
            f"trailer\n<< /Size {catalog_id + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(out)


def generar_pdf_texto(file_path, titulo, lineas, subtitulo=None):
    page_w, page_h = 595, 842
    margin_x, top_y, bottom_y = 50, 800, 60
    leading = 14
    max_lines = int((top_y - bottom_y) / leading)

    all_lines = []
    if titulo:
        all_lines.append(("title", str(titulo)))
    if subtitulo:
        all_lines.append(("sub", str(subtitulo)))
    all_lines.append(("sp", ""))
    for ln in lineas:
        all_lines.append(("body", str(ln)))

    pages = []
    current = []
    for kind, txt in all_lines:
        if kind == "title":
            current.append(("F1", 18, txt))
        elif kind == "sub":
            current.append(("F1", 12, txt))
        elif kind == "sp":
            current.append(("F1", 12, ""))
        else:
            wrapped = _wrap_text_lines(txt, 95)
            for w in wrapped:
                current.append(("F1", 11, w))
        if len(current) >= max_lines:
            pages.append(current)
            current = []
    if current:
        pages.append(current)

    offsets = []
    out = bytearray()

    def add_obj(obj_bytes):
        offsets.append(len(out))
        out.extend(obj_bytes)

    out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    font_obj_id = 1
    add_obj(b"1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    pages_obj_id = 2
    page_ids = []
    content_ids = []
    next_id = 3

    for _ in pages:
        content_ids.append(next_id)
        next_id += 1
        page_ids.append(next_id)
        next_id += 1

    catalog_id = next_id

    for page_idx, page_lines in enumerate(pages):
        content_stream = bytearray()
        content_stream.extend(b"BT\n")
        content_stream.extend(b"/F1 11 Tf\n")
        content_stream.extend(b"14 TL\n")
        content_stream.extend(f"1 0 0 1 {margin_x} {top_y} Tm\n".encode("ascii"))

        first = True
        for font_name, font_size, txt in page_lines:
            if not first:
                content_stream.extend(b"T*\n")
            first = False
            content_stream.extend(f"/{font_name} {font_size} Tf\n".encode("ascii"))
            content_stream.extend(b"(")
            content_stream.extend(_pdf_escape_bytes(txt))
            content_stream.extend(b") Tj\n")
        content_stream.extend(b"ET\n")

        stream_header = f"{content_ids[page_idx]} 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("ascii")
        stream_footer = b"endstream\nendobj\n"
        add_obj(stream_header + content_stream + stream_footer)

        page_obj = (
            f"{page_ids[page_idx]} 0 obj\n"
            f"<< /Type /Page /Parent {pages_obj_id} 0 R /MediaBox [0 0 {page_w} {page_h}] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_ids[page_idx]} 0 R >>\nendobj\n"
        ).encode("ascii")
        add_obj(page_obj)

    kids = " ".join([f"{pid} 0 R" for pid in page_ids])
    pages_obj = f"{pages_obj_id} 0 obj\n<< /Type /Pages /Kids [ {kids} ] /Count {len(page_ids)} >>\nendobj\n".encode(
        "ascii"
    )
    add_obj(pages_obj)

    catalog_obj = f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_obj_id} 0 R >>\nendobj\n".encode("ascii")
    add_obj(catalog_obj)

    xref_start = len(out)
    out.extend(f"xref\n0 {catalog_id + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        (
            f"trailer\n<< /Size {catalog_id + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(out)


def _get_default_printer_name():
    import ctypes
    from ctypes import wintypes

    get_default = ctypes.windll.winspool.GetDefaultPrinterW
    size = wintypes.DWORD(0)
    get_default(None, ctypes.byref(size))
    if not size.value:
        return None
    buf = ctypes.create_unicode_buffer(size.value)
    ok = get_default(buf, ctypes.byref(size))
    if not ok:
        return None
    name = str(buf.value or "").strip()
    return name or None


def _list_printers_windows():
    import ctypes
    from ctypes import wintypes

    PRINTER_ENUM_LOCAL = 2
    PRINTER_ENUM_CONNECTIONS = 4

    class PRINTER_INFO_4(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    EnumPrintersW = ctypes.windll.winspool.EnumPrintersW
    flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
    needed = wintypes.DWORD(0)
    returned = wintypes.DWORD(0)
    EnumPrintersW(flags, None, 4, None, 0, ctypes.byref(needed), ctypes.byref(returned))
    if not needed.value:
        return []
    buf = ctypes.create_string_buffer(needed.value)
    ok = EnumPrintersW(flags, None, 4, buf, needed, ctypes.byref(needed), ctypes.byref(returned))
    if not ok or not returned.value:
        return []
    arr = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_4))
    out = []
    for i in range(int(returned.value)):
        name = str(arr[i].pPrinterName or "").strip()
        if name:
            out.append(name)
    return out


def _shell_print_text_windows(text, doc_name="Ticket"):
    import ctypes
    import os
    import tempfile
    from datetime import datetime

    tmp_dir = tempfile.gettempdir()
    safe = "".join([c for c in str(doc_name or "Ticket") if c.isalnum() or c in (" ", "-", "_")]).strip() or "Ticket"
    fname = f"{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(tmp_dir, fname)
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(str(text or ""))

    rc = ctypes.windll.shell32.ShellExecuteW(None, "print", path, None, None, 0)
    if rc <= 32:
        raise RuntimeError("No se pudo imprimir mediante el sistema (ShellExecute)")
    return path


def listar_impresoras():
    return _list_printers_windows()


def impresora_predeterminada():
    return _get_default_printer_name()


def _print_raw_windows(text, printer_name=None, doc_name="Ticket"):
    import ctypes
    from ctypes import wintypes

    if printer_name is None:
        printer_name = _get_default_printer_name()
    if not printer_name:
        printers = _list_printers_windows()
        if printers:
            raise RuntimeError("No se encontró una impresora predeterminada. Impresoras detectadas: " + ", ".join(printers))
        raise RuntimeError("No se encontró una impresora predeterminada")

    class DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", wintypes.LPWSTR),
            ("pOutputFile", wintypes.LPWSTR),
            ("pDatatype", wintypes.LPWSTR),
        ]

    OpenPrinterW = ctypes.windll.winspool.OpenPrinterW
    ClosePrinter = ctypes.windll.winspool.ClosePrinter
    StartDocPrinterW = ctypes.windll.winspool.StartDocPrinterW
    EndDocPrinter = ctypes.windll.winspool.EndDocPrinter
    StartPagePrinter = ctypes.windll.winspool.StartPagePrinter
    EndPagePrinter = ctypes.windll.winspool.EndPagePrinter
    WritePrinter = ctypes.windll.winspool.WritePrinter

    hPrinter = wintypes.HANDLE()
    if not OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
        raise RuntimeError(f"No se pudo abrir la impresora: {printer_name}")
    try:
        di = DOC_INFO_1(str(doc_name), None, "RAW")
        job = StartDocPrinterW(hPrinter, 1, ctypes.byref(di))
        if not job:
            raise RuntimeError("No se pudo iniciar el documento de impresión")
        try:
            if not StartPagePrinter(hPrinter):
                raise RuntimeError("No se pudo iniciar la página de impresión")
            try:
                if text is None:
                    text = ""
                raw_text = str(text).replace("\n", "\r\n").encode("cp437", "replace")
                payload = b"\x1b@\x1bt\x00" + raw_text
                payload += b"\r\n\r\n\x1dV\x00"
                written = wintypes.DWORD(0)
                ok = WritePrinter(hPrinter, payload, len(payload), ctypes.byref(written))
                if not ok:
                    raise RuntimeError("No se pudo enviar el ticket a la impresora")
            finally:
                EndPagePrinter(hPrinter)
        finally:
            EndDocPrinter(hPrinter)
    finally:
        ClosePrinter(hPrinter)


def imprimir_ticket_texto(titulo, lineas, subtitulo=None, printer_name=None, max_chars=42):
    max_chars = int(max_chars or 42)

    def _center(s):
        s = str(s or "")
        if len(s) >= max_chars:
            return s
        pad = (max_chars - len(s)) // 2
        return (" " * pad) + s

    out_lines = []
    if subtitulo:
        for w in _wrap_text_lines(subtitulo, max_chars):
            out_lines.append(_center(w))
    if titulo:
        for w in _wrap_text_lines(titulo, max_chars):
            out_lines.append(_center(w))
    out_lines.append("")
    for ln in (lineas or []):
        for w in _wrap_text_lines(ln, max_chars):
            out_lines.append(w)
    out_lines.append("")
    out_lines.append("")

    payload = "\n".join(out_lines)
    try:
        _print_raw_windows(payload, printer_name=printer_name, doc_name=str(titulo or "Ticket"))
    except Exception:
        _shell_print_text_windows(payload, doc_name=str(titulo or "Ticket"))
