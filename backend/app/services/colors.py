import webcolors


def get_color_name(hex_color: str) -> str | None:
    rgb_color = webcolors.hex_to_rgb(hex_color)

    try:
        return webcolors.rgb_to_name(rgb_color, spec="CSS3")
    except ValueError:
        pass

    # Buscar el más cercano por distancia euclidiana
    min_distance = float("inf")
    closest_name = None

    for name in webcolors.names("css3"):
        r, g, b = webcolors.name_to_rgb(name)
        distance = (
            (r - rgb_color[0]) ** 2 + (g - rgb_color[1]) ** 2 + (b - rgb_color[2]) ** 2
        )
        if distance < min_distance:
            min_distance = distance
            closest_name = name

    return closest_name
