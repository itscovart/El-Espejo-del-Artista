import cv2, base64
import numpy as np


def get_image_from_data_url(bin_img: bytes):
    img = cv2.imdecode(np.frombuffer(bin_img, np.uint8), cv2.IMREAD_COLOR)
    img_color = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_color

def get_binary_type_from_data_url(data_url: str) -> dict[str, str]:
    content = data_url.split(',')
    type_img = content[0].split(';')[0].split('/')[1]
    res = {}
    res["type_img"] = type_img
    base64_img = "".join(content[1].split())
    bin_img = base64.b64decode(base64_img)
    res["bin_img"] = bin_img
    return res

def get_values_image(img_color: np.ndarray) -> dict[str, int]:

    res_example = {"contrast": 78}
    return res_example
