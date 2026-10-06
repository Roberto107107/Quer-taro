"""Validate uploaded raster images and store only decoded/re-encoded pixels."""
from io import BytesIO
from pathlib import Path
import secrets
import warnings
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

def image_folder():
    return Path(current_app.config['UPLOAD_FOLDER']) / 'imagenes'

def save_image(upload):
    if not upload or not upload.filename:
        return None
    data = upload.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise ValueError('La imagen debe pesar como máximo 5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as original:
                if original.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValueError('Selecciona una imagen JPG, PNG o WebP.')
                if original.width * original.height > 20_000_000:
                    raise ValueError('La imagen no debe superar 20 megapíxeles.')
                original.load()
                pixels = ImageOps.exif_transpose(original).convert('RGBA')
                pixels.thumbnail((2400, 2400))
                output = BytesIO()
                pixels.save(output, format='WEBP', quality=90)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('No se pudo leer la imagen. Usa un JPG, PNG o WebP válido.') from None
    folder = image_folder()
    folder.mkdir(parents=True, exist_ok=True)
    filename = secrets.token_hex(24) + '.webp'
    target = folder / filename
    try:
        target.write_bytes(output.getvalue())
    except OSError:
        target.unlink(missing_ok=True)
        raise
    return filename

def remove_image(filename):
    if filename:
        try:
            (image_folder() / filename).unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning('No se pudo eliminar una imagen reemplazada o retirada.')
