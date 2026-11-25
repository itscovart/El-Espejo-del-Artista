from decimal import Decimal
import cv2
import numpy as np
from sklearn.cluster import KMeans

FORMATOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MAX_BYTES = 10 * 1024 * 1024
LADO_MAXIMO_PX = 1024
DIMENSION_MINIMA_PX = 32
MUESTRAS_KMEANS = 10_000


class ImagenNoAnalizableError(ValueError):
    pass


def _normalizar_a_bgr(imagen: np.ndarray) -> np.ndarray:
    if imagen.dtype == np.uint16:
        imagen = (imagen / 256).astype(np.uint8)

    if imagen.ndim == 2:
        return cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)

    if imagen.shape[2] == 4:
        bgr = imagen[:, :, :3].astype(np.float32)
        alfa = imagen[:, :, 3:4].astype(np.float32) / 255.0
        fondo_blanco = np.full_like(bgr, 255.0)
        compuesta = bgr * alfa + fondo_blanco * (1.0 - alfa)
        return np.clip(compuesta, 0, 255).astype(np.uint8)

    return imagen[:, :, :3]


def _decodificar_imagen(contenido: bytes) -> np.ndarray:
    if not contenido:
        raise ImagenNoAnalizableError("El archivo recibido está vacío.")
    if len(contenido) > TAMANO_MAX_BYTES:
        raise ImagenNoAnalizableError("La imagen supera el límite máximo de 10 MB.")

    arreglo = np.frombuffer(contenido, dtype=np.uint8)
    imagen = cv2.imdecode(arreglo, cv2.IMREAD_UNCHANGED)

    if imagen is None:
        raise ImagenNoAnalizableError(
            "No se pudo leer la imagen. Verifica que sea un JPG, PNG o WEBP válido."
        )

    imagen_bgr = _normalizar_a_bgr(imagen)
    alto, ancho = imagen_bgr.shape[:2]
    if alto < DIMENSION_MINIMA_PX or ancho < DIMENSION_MINIMA_PX:
        raise ImagenNoAnalizableError(
            "La imagen es demasiado pequeña para extraer métricas visuales confiables."
        )

    return imagen_bgr


def _redimensionar_copia(imagen_bgr: np.ndarray) -> np.ndarray:
    alto, ancho = imagen_bgr.shape[:2]
    lado_mayor = max(alto, ancho)

    if lado_mayor <= LADO_MAXIMO_PX:
        return imagen_bgr

    escala = LADO_MAXIMO_PX / float(lado_mayor)
    nuevo_ancho = max(1, int(round(ancho * escala)))
    nuevo_alto = max(1, int(round(alto * escala)))
    return cv2.resize(imagen_bgr, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)


def _extraer_paleta_color(imagen_bgr: np.ndarray, k: int = 5) -> dict:
    imagen_lab = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2LAB)
    pixeles_lab = imagen_lab.reshape(-1, 3)

    if len(pixeles_lab) > MUESTRAS_KMEANS:
        rng = np.random.default_rng(seed=42)
        indices = rng.choice(len(pixeles_lab), size=MUESTRAS_KMEANS, replace=False)
        muestra = pixeles_lab[indices]
    else:
        muestra = pixeles_lab

    colores_unicos = len(np.unique(muestra, axis=0))
    n_clusters = max(1, min(k, colores_unicos))

    modelo = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
    etiquetas = modelo.fit_predict(muestra)
    conteos = np.bincount(etiquetas)

    centroides_lab = np.clip(np.round(modelo.cluster_centers_), 0, 255).astype(np.uint8)
    centroides_rgb = cv2.cvtColor(centroides_lab.reshape(1, -1, 3), cv2.COLOR_LAB2RGB)[0]

    total = float(conteos.sum())
    colores = []
    for rgb, cantidad in zip(centroides_rgb, conteos):
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        colores.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "porcentaje": round((float(cantidad) / total) * 100.0, 2),
            }
        )

    colores.sort(key=lambda item: item["porcentaje"], reverse=True)
    return {"colores": colores}


def _calcular_iluminacion_y_contraste(imagen_bgr: np.ndarray) -> tuple[Decimal, Decimal]:
    grises = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    desviacion = float(np.std(grises))
    if desviacion < 1.0:
        raise ImagenNoAnalizableError(
            "La imagen parece completamente plana o en blanco; sube una obra con trazos visibles."
        )

    iluminacion = float(np.mean(grises) / 255.0 * 100.0)
    contraste = min(100.0, (desviacion / 127.5) * 100.0)

    return Decimal(f"{iluminacion:.2f}"), Decimal(f"{contraste:.2f}")


def _calcular_balance_compositivo(imagen_bgr: np.ndarray) -> Decimal:
    grises = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    gx = cv2.Sobel(grises, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(grises, cv2.CV_32F, 0, 1, ksize=3)
    peso_visual = cv2.magnitude(gx, gy)

    alto, ancho = peso_visual.shape
    mitad_y, mitad_x = alto // 2, ancho // 2

    izq = float(np.sum(peso_visual[:, :mitad_x]))
    der = float(np.sum(peso_visual[:, mitad_x:]))
    arr = float(np.sum(peso_visual[:mitad_y, :]))
    abj = float(np.sum(peso_visual[mitad_y:, :]))

    simetria_lr = 1.0 - abs(izq - der) / (izq + der + 1e-6)
    simetria_tb = 1.0 - abs(arr - abj) / (arr + abj + 1e-6)
    puntaje_simetria = ((simetria_lr + simetria_tb) / 2.0) * 100.0

    peso_total = float(np.sum(peso_visual))
    if peso_total <= 1e-6:
        puntaje_tercios = 50.0
    else:
        ys, xs = np.indices((alto, ancho), dtype=np.float32)
        cx = float(np.sum(xs * peso_visual) / peso_total) / max(ancho - 1, 1)
        cy = float(np.sum(ys * peso_visual) / peso_total) / max(alto - 1, 1)

        puntos_tercios = [
            (1 / 3, 1 / 3),
            (2 / 3, 1 / 3),
            (1 / 3, 2 / 3),
            (2 / 3, 2 / 3),
        ]
        dist_min = min(np.hypot(cx - px, cy - py) for px, py in puntos_tercios)
        dist_max = float(np.hypot(1 / 3, 1 / 3))
        puntaje_tercios = max(0.0, (1.0 - dist_min / dist_max)) * 100.0

    balance = 0.5 * puntaje_simetria + 0.5 * puntaje_tercios
    return Decimal(f"{min(100.0, max(0.0, balance)):.2f}")


def analizar_imagen_bytes(contenido: bytes, content_type: str | None = None) -> dict:
    if content_type and content_type.lower() not in FORMATOS_PERMITIDOS:
        raise ImagenNoAnalizableError(
            "Formato no permitido. Solo se aceptan imágenes JPG, PNG o WEBP."
        )

    imagen_bgr = _decodificar_imagen(contenido)
    copia = _redimensionar_copia(imagen_bgr)

    iluminacion, contraste = _calcular_iluminacion_y_contraste(copia)
    balance = _calcular_balance_compositivo(copia)
    paleta = _extraer_paleta_color(copia, k=5)

    return {
        "paleta_color": paleta,
        "contraste": contraste,
        "iluminacion": iluminacion,
        "balance_compositivo": balance,
        "estado": "completado",
    }