from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from sqlalchemy.orm import Session


from ..database.connection import get_db
from ..schemas.works import AnalizeImage, Gallery, GalleryWorkResponse, ResultImageResponse
from ..models.obra import Obra
from ..models.analisis import Analisis
from ..models.critica import Critica
from ..models.ejercicio import Ejercicio
from ..services.images import analize_bytes_images, upload_image_cloud
from ..errors.errorHandle import NotAnalizableImage
from ..services.colors import get_color_name

router = APIRouter(prefix="/works")


@router.post("/analize")
def analize_image(image: AnalizeImage, db: Session = Depends(get_db)):
    try:
        title = image.work_title
        response = upload_image_cloud(data_url=image.data_url, work_title=title)

        image_url_cloud = response.url if response.url is not None else "Obra"
        new_work = Obra(
            id_usuario=image.user_id,
            titulo_obra=title,
            ruta_archivo_imagen=image_url_cloud,
            fecha_subida=datetime.now().isoformat(),
        )

        db.add(new_work)
        db.commit()
        db.refresh(new_work)

        if new_work:

            result_analize = analize_bytes_images(data_url=image.data_url)
            colors = result_analize["color-palette"]["colors"]

            artwork_data = {
                "work_id": new_work.id_obra,
                "title": new_work.titulo_obra,
                "work_url": new_work.ruta_archivo_imagen,
                "date": new_work.fecha_subida,
            }

            contrast = result_analize["contrast"]
            ilumination = result_analize["ilumination"]
            compositive_balance = result_analize["compositive-balance"]

            metrics_data = [int(contrast), int(ilumination), int(compositive_balance)]

            palette_data = [
                {"name": get_color_name(data["hex"]), "hex_color": data["hex"]}
                for data in colors
            ]

            new_analisis = Analisis(
                id_obra=new_work.id_obra,
                id_usuario=image.user_id,
                paleta_color={
                    "colors": [
                        {"name": get_color_name(data["hex"]), "hex_color": data["hex"]}
                        for data in colors
                    ]
                },
                contraste=contrast,
                iluminacion=ilumination,
                balance_compositivo=compositive_balance,
                estado="Pendiente",
                fecha_analisis=datetime.now().isoformat(),
            )

            db.add(new_analisis)
            db.commit()
            db.refresh(new_analisis)

            if new_analisis is None:
                raise HTTPException(
                    status_code=500, detail="Hubo un error al registrar el analisis"
                )

            new_critique = Critica(
                id_analisis=new_analisis.id_analisis,
                texto_critica="",
                fecha_generacion=datetime.now().isoformat(),
            )

            db.add(new_critique)
            db.commit()
            db.refresh(new_critique)

            if new_critique is None:
                raise HTTPException(
                    status_code=500, detail="Ocurrio un error al registrar la critica"
                )

            new_exercise = Ejercicio(
                id_critica=new_critique.id_critica,
                titulo_ejercicio="",
                descripcion="",
                estado="Pendiente",
                fecha_asignacion=datetime.now().isoformat(),
            )

            db.add(new_exercise)
            db.commit()
            db.refresh(new_exercise)

            if new_exercise is None:
                raise HTTPException(
                    status_code=500, detail="Ocurrio un error al registrar el ejercicio"
                )

            return new_work.id_obra

        else:
            raise HTTPException(status_code=422, detail="Analisis no encontrado")
    except NotAnalizableImage as err:
        return err


@router.get("/find")
def get_work(id_work: int | None, db: Session = Depends(get_db)):
    if id_work is None:
        raise HTTPException(
            status_code=500,
            detail="Ocurrio un error con el servidor al hacer la consulta",
        )

    work = db.query(Obra).filter(Obra.id_obra == id_work).first()

    if work:
        return work

    raise HTTPException(status_code=422, detail="Obra no encontrada")


@router.get("/analize-get")
def get_analize_work(
    image_id: int = Query(...),
    db: Session = Depends(get_db),
):

    if image_id is None:
        raise NotAnalizableImage

    work = db.query(Obra).filter(Obra.id_obra == image_id).first()
    if work is None:
        raise HTTPException(
            status_code=422, detail="Hubo un error al encontrar la Obra"
        )

    analisis = db.query(Analisis).filter(Analisis.id_obra == image_id).first()
    if analisis is None:
        raise HTTPException(
            status_code=422, detail="Hubo un error al encontrar el Analisis"
        )

    critique = (
        db.query(Critica).filter(Critica.id_analisis == analisis.id_analisis).first()
    )
    if critique is None:
        raise HTTPException(
            status_code=422, detail="Hubo un error al encontrar la Critica"
        )

    exercise = (
        db.query(Ejercicio).filter(Ejercicio.id_critica == critique.id_analisis).first()
    )
    if exercise is None:
        raise HTTPException(
            status_code=422, detail="Hubo un error al encontrar el Ejercicio"
        )

    artwork_data = {
        "work_id": work.id_obra,
        "title": work.titulo_obra,
        "work_url": work.ruta_archivo_imagen,
        "date": work.fecha_subida,
    }

    metrics_data = [
        int(analisis.contraste),
        int(analisis.iluminacion),
        int(analisis.balance_compositivo),
    ]

    colors = analisis.paleta_color["colors"]

    palette_data = [
        {"name": data["name"], "hex_color": data["hex_color"]} for data in colors
    ]

    exercise_data = {
        "title": exercise.titulo_ejercicio,
        "description": exercise.descripcion,
        "status": exercise.estado,
    }

    result_response = ResultImageResponse(
        artwork=artwork_data,
        status="Completado",
        metrics=metrics_data,
        palette=palette_data,
        critique=critique.texto_critica,
        exercise=exercise_data,
    )

    return result_response

    raise HTTPException(status_code=422, detail="Analisis no encontrada")


@router.post("/gallery")
def get_gallery_user(data: Gallery, db: Session = Depends(get_db)):
    user_id = data.user_id
    if user_id is None:
        raise HTTPException(
            status_code=500,
            detail="Ocurrio un error al consultar la galeria del usuario",
        )

    gallery = db.query(Obra).filter(Obra.id_usuario == user_id).all()

    response_arr = []
    for work in gallery:
        new_response = GalleryWorkResponse(
            title=work.titulo_obra,
            image_url=work.ruta_archivo_imagen,
            date=work.fecha_subida,
        )

        response_arr.append(new_response)

    return response_arr
