import os
import base64
from decimal import Decimal
from dotenv import load_dotenv
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import KMeans
from imagekitio import ImageKit

from ..errors.errorHandle import NotAnalizableImage

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

_MAX_BYTES_SIZE = 100 * 1024 * 1024
_MINIMUN_DIMENSION_PX = 32
_MAXIMUM_SIDE_PX = 1024
_KMEANS_SAMPLES = 1000


def _get_image_from_data_url(bin_img: bytes):
    img = cv2.imdecode(np.frombuffer(bin_img, np.uint8), cv2.IMREAD_COLOR)
    img_color = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_color


def _get_binary_type_from_data_url(data_url: str) -> tuple[str, bytes]:
    content = data_url.split(",")
    type_img = content[0].split(";")[0].split("/")[1]

    base64_img = "".join(content[1].split())
    bin_img = base64.b64decode(base64_img)

    return type_img, bin_img


def upload_image_cloud(data_url: str, work_title: str = "Obra"):
    type_img, bin_img = _get_binary_type_from_data_url(data_url)

    load_dotenv(_ENV_PATH)
    image_kit_key = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
    folder_name = os.getenv("IMAGEKIT_FOLDER_NAME", "")
    client = ImageKit(private_key=image_kit_key)

    response = client.files.upload(
        file=bin_img, file_name=work_title, folder=folder_name
    )

    return response


def _bgr_normalize(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint16:
        image = (image / 256).astype(np.uint8)

    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.shape[2] == 4:
        bgr = image[:, :, :3].astype(np.float32)
        alpha = image[:, :, 3:4].astype(np.float32) / 255.0
        white_bg = np.full_like(bgr, 255.0)
        composed = bgr * alpha + white_bg * (1.0 - alpha)
        return np.clip(composed, 0, 255).astype(np.uint8)

    return image[:, :, :3]


def _decode_image(content: bytes) -> np.ndarray:
    if len(content) > _MAX_BYTES_SIZE:
        raise NotAnalizableImage("La imagen supera el limite de 100 MB.")

    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

    if image is None:
        raise NotAnalizableImage(
            "No se pudo leer la imagen, Verifica que efectivamente sea un JPG, PNG o WEBP."
        )

    bgr_image = _bgr_normalize(image)
    height, width = bgr_image.shape[:2]
    if height < _MINIMUN_DIMENSION_PX or width < _MINIMUN_DIMENSION_PX:
        raise NotAnalizableImage(
            "La imagen es demasiado pequeña para extraer métricas visuales confiables"
        )

    return bgr_image


def _copy_redimension(bgr_image: np.ndarray) -> np.ndarray:
    height, width = bgr_image.shape[:2]
    bigger_side = max(height, width)

    if bigger_side <= _MAXIMUM_SIDE_PX:
        return bgr_image

    scale = _MAXIMUM_SIDE_PX / float(bigger_side)
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    return cv2.resize(bgr_image, (new_width, new_height), interpolation=cv2.INTER_AREA)


def _get_color_palette(bgr_image: np.ndarray, k: int = 5) -> dict:
    lab_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
    lab_pixels = lab_image.reshape(-1, 3)

    if len(lab_pixels) > _KMEANS_SAMPLES:
        rng = np.random.default_rng(seed=42)
        idxs = rng.choice(len(lab_pixels), size=_KMEANS_SAMPLES, replace=False)
        sample = lab_pixels[idxs]
    else:
        sample = lab_pixels

    unique_colors = len(np.unique(sample, axis=0))
    n_clusters = max(1, min(k, unique_colors))

    model = KMeans(
        n_clusters=n_clusters, n_init="auto", random_state=42, algorithm="elkan"
    )
    tags = model.fit_predict(sample)
    counts = np.bincount(tags)

    lad_centroids = np.clip(np.round(model.cluster_centers_), 0, 255).astype(np.uint8)
    rgb_centroids = cv2.cvtColor(lad_centroids.reshape(1, -1, 3), cv2.COLOR_LAB2RGB)[0]

    total = float(counts.sum())
    colors = []
    for rgb, quantity in zip(rgb_centroids, counts):
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        colors.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "percentage": round((float(quantity) / total) * 100.0, 2),
            }
        )

    colors.sort(key=lambda item: item["percentage"], reverse=True)
    return {"colors": colors}


def _get_ilumination_contraste(bgr_image: np.ndarray) -> tuple[Decimal, Decimal]:
    grays = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY).astype(np.float32)

    deviation = float(np.std(grays))
    if deviation < 1.0:
        raise NotAnalizableImage(
            "La imagen parece completamente plana o en blanco, sube una obra con datos visibles."
        )

    ilumination = float(np.mean(grays) / 255.0 * 100.0)
    contrast = min(100.0, (deviation / 127.5) * 100.0)

    return Decimal(f"{ilumination:.2f}"), Decimal(f"{contrast:.2f}")


def _get_compositive_balance(bgr_image: np.ndarray) -> Decimal:
    grays = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY).astype(np.float32)

    gx = cv2.Sobel(grays, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(grays, cv2.CV_32F, 0, 1, ksize=3)
    visual_weight = cv2.magnitude(gx, gy)

    height, width = visual_weight.shape
    half_y, half_x = height // 2, width // 2

    left = float(np.sum(visual_weight[:, :half_x]))
    right = float(np.sum(visual_weight[:, half_x:]))
    up = float(np.sum(visual_weight[:half_y, :]))
    down = float(np.sum(visual_weight[half_y:, :]))

    simmetry_lr = 1.0 - abs(left - right) / (left + right + 1e-6)
    simmetry_tb = 1.0 - abs(up - down) / (up + down + 1e-6)
    simmetry_score = ((simmetry_lr + simmetry_tb) / 2.0) * 100.0

    total_weight = float(np.sum(visual_weight))
    if total_weight <= 1e-6:
        thirds_score = 50.0
    else:
        ys, xs = np.indices((height, width), dtype=np.float32)
        cx = float(np.sum(xs * visual_weight) / total_weight) / max(width - 1, 1)
        cy = float(np.sum(ys * visual_weight) / total_weight) / max(height - 1, 1)

        thirds_points = [
            (1 / 3, 1 / 3),
            (2 / 3, 1 / 3),
            (1 / 3, 2 / 3),
            (2 / 3, 2 / 3),
        ]
        min_dist = min(np.hypot(cx - px, cy - py) for px, py in thirds_points)
        max_dist = float(np.hypot(1 / 3, 1 / 3))
        thirds_score = max(0.0, (1.0 - min_dist / max_dist)) * 100.0

    balance = 0.5 * simmetry_score + 0.5 * thirds_score
    return Decimal(f"{min(100.0, max(0.0, balance)):.2f}")


def analize_bytes_images(data_url: str) -> dict:
    _, bin_img = _get_binary_type_from_data_url(data_url)

    copy = _copy_redimension(_decode_image(bin_img))

    ilumination, contrast = _get_ilumination_contraste(copy)
    balance = _get_compositive_balance(copy)
    palette = _get_color_palette(copy, k=5)

    return {
        "color-palette": palette,
        "contrast": contrast,
        "ilumination": ilumination,
        "compositive-balance": balance,
        "status": "completed",
    }
