from __future__ import annotations
import re

BRANDS = {
    "volkswagen": ["#volkswagen", "#vw", "#фольксваген"],
    "toyota": ["#toyota", "#тойота"],
    "bmw": ["#bmw", "#бмв"],
    "mercedes": ["#mercedes", "#мерседес"],
    "audi": ["#audi", "#ауди"],
    "hyundai": ["#hyundai", "#хендай", "#хундай"],
    "kia": ["#kia", "#киа"],
    "nissan": ["#nissan", "#ниссан"],
    "honda": ["#honda", "#хонда"],
    "mazda": ["#mazda", "#мазда"],
    "lexus": ["#lexus", "#лексус"],
    "porsche": ["#porsche", "#порше"],
    "land rover": ["#landrover", "#ленд ровер"],
    "range rover": ["#rangerover", "#рейнджровер"],
    "chery": ["#chery", "#чери"],
    "geely": ["#geely", "#джили"],
    "haval": ["#haval", "#хавал"],
    "changan": ["#changan", "#чанган"],
    "byd": ["#byd", "#бид"],
    "exeed": ["#exeed", "#эксид"],
    "lixiang": ["#lixiang", "#лисян"],
    "zeekr": ["#zeekr", "#зикр"],
    "nio": ["#nio", "#нио"],
    "tank": ["#tank", "#танк"],
}

MODELS = {
    "tayron": ["#tayron", "#тайрон"],
    "tiguan": ["#tiguan", "#тигуан"],
    "tucson": ["#tucson", "#туксон"],
    "camry": ["#camry", "#камри"],
    "rav4": ["#rav4", "#рав4"],
    "x5": ["#bmwx5"],
    "x3": ["#bmwx3"],
    "cx5": ["#cx5", "#мазда cx5"],
    "cx-5": ["#cx5"],
    "h6": ["#havalh6"],
    "coolray": ["#coolray"],
    "atlas": ["#atlas", "#атлас"],
    "eq6": ["#eq6"],
    "emgrand": ["#emgrand"],
    "monjaro": ["#monjaro"],
}

GENERAL = [
    "#авто", "#автомобиль", "#купитьавто", "#автосалон",
    "#автоизкитая", "#параллельныйимпорт", "#автоподбор",
    "#продажаавто", "#автобизнес", "#carsforsale",
]


def generate_hashtags(text: str) -> str:
    text_lower = text.lower()
    tags: list[str] = []

    for brand, brand_tags in BRANDS.items():
        if brand in text_lower:
            tags.extend(brand_tags)

    for model, model_tags in MODELS.items():
        if model in text_lower:
            tags.extend(model_tags)

    tags.extend(GENERAL)

    # Убираем дубли
    seen = set()
    unique = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return " ".join(unique)
