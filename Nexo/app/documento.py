"""Check document containers without executing, extracting or trusting MIME headers."""
from io import BytesIO
from pathlib import Path
import warnings
from zipfile import ZipFile, BadZipFile
from PIL import Image

def validate_document(upload, filename):
    data = upload.read(10 * 1024 * 1024 + 1)
    upload.stream.seek(0)
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError('El documento debe contener datos y no superar 10 MB.')
    ext = Path(filename).suffix.lower()
    valid = False
    try:
        if ext == '.pdf':
            valid = data.startswith(b'%PDF-') and b'%%EOF' in data[-4096:]
        elif ext == '.txt':
            valid = b'\x00' not in data
        elif ext in ('.png', '.jpg', '.jpeg'):
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    valid = image.format == ('PNG' if ext == '.png' else 'JPEG') and image.width * image.height <= 20_000_000
                    image.verify()
        elif ext in ('.docx', '.xlsx'):
            with ZipFile(BytesIO(data)) as archive:
                entries = archive.infolist()
                names = {entry.filename for entry in entries}
                expected = 'word/document.xml' if ext == '.docx' else 'xl/workbook.xml'
                valid = ('[Content_Types].xml' in names and expected in names
                         and len(entries) <= 10000
                         and sum(e.file_size for e in entries) <= 100 * 1024 * 1024
                         and not any('vbaproject' in name.lower() for name in names))
    except (OSError, ValueError, BadZipFile, Image.DecompressionBombError, Image.DecompressionBombWarning):
        valid = False
    if not valid:
        raise ValueError('El contenido del archivo no corresponde a un documento permitido y válido.')
