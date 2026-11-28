from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import TypedDict


class AnalizeImage(BaseModel):
    user_id: int
    work_title: str = Field(default="Obra", max_length=120)
    data_url: str


class ResultImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artwork: dict[str, str | datetime]
    status: str
    metrics: list[int]
    palette: list[dict[str, str]]
    critique: str
    exercise: dict[str, str]

class Gallery(BaseModel):
    user_id: int

class GalleryWorkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    image_url: str
    date: datetime
