# ruff: noqa: E501  (verbatim table text is kept unbroken)
"""Tables 7 and 8 of Decreto 80/2023, from the official DOGV text (num. 9609, 2 June 2023, pp. 34133-34135).

Transcribed from the gazette PDF (https://dogv.gva.es/datos/2023/06/02/pdf/2023_6094.pdf) and
checked against the page images. Each table exists twice on purpose: as `*_QUOTE`, the rows
copied as text, and as the data the rules use. A test parses the quote and compares it with the
data, so the two transcriptions cannot silently disagree. A person should still check both
against the DOGV before relying on them.
"""

# Maximum number of occupants of the dwelling, by column.
TABLE7_OCCUPANTS = (2, 4, 6, 8, 9)  # the last column is "≥9"

TABLE_7_QUOTE = """\
Tabla 7. Superficie útil mínima de los recintos (m²)
Núm. máximo de ocupantes de la vivienda: 2 4 6 8 ≥9
Dormitorio doble principal (1): 10
Resto de dormitorios dobles (1): 8
Dormitorio sencillo: 6
Cocina: 6 7 8 9 10
Comedor: 7 8 9 10 11
Cocina-comedor: 11 13 15 17 19
Estar: 12 13 14 15 16
Estar-comedor: 14 16 18 20 22
Estar-comedor-cocina: 19 22 25 28 31
Dormitorio-estar-comedor-cocina: 29 – – – –
Baño (2) (3): 4
Aseo (3): 2
Lavadero (4): 2
(1) Será posible reducir la superficie mínima de los dormitorios colindantes a zonas de circulación hasta un 20 %, de forma que otros usos del dormitorio distintos al de descanso, como los de estudio o trabajo, se puedan ubicar en estas zonas de circulación, siempre que en el dormitorio se puedan inscribir las figuras correspondientes establecidas en el artículo 56. Para ello estas zonas dispondrán de la superficie mínima restante, tendrán una anchura mínima de 1,80 m, y contarán con la iluminación y ventilación natural prevista en los artículos 62 y 63.
(2) Al menos un baño tendrá aquesta superficie, pudiendo el resto de los baños tener una superficie mínima de 3 m².
(3) En caso de compartimentación del espacio para evacuación fisiológica, aquest recinto tendrá como mínimo una superficie de 1,50 m².
(4) Si el lavadero se integra en la cocina, en el baño o en el aseo, no se exigirá aquesta superficie y la de la cocina, baño o aseo se incrementará en 1 m².
"""

# Rows of table 7: area in m² for each occupant column; None = not allowed ("–").
TABLE_7: dict[str, tuple[float | None, ...]] = {
    "dormitorio_doble_principal": (10, 10, 10, 10, 10),
    "dormitorio_doble": (8, 8, 8, 8, 8),
    "dormitorio_sencillo": (6, 6, 6, 6, 6),
    "cocina": (6, 7, 8, 9, 10),
    "comedor": (7, 8, 9, 10, 11),
    "cocina_comedor": (11, 13, 15, 17, 19),
    "estar": (12, 13, 14, 15, 16),
    "estar_comedor": (14, 16, 18, 20, 22),
    "estar_comedor_cocina": (19, 22, 25, 28, 31),
    "dormitorio_estar_comedor_cocina": (29, None, None, None, None),
    "bano": (4, 4, 4, 4, 4),
    "aseo": (2, 2, 2, 2, 2),
    "lavadero": (2, 2, 2, 2, 2),
}
OTHER_BATH_MIN_M2 = 3.0  # table 7 note (2): the other baths
COMPARTMENTED_WC_MIN_M2 = 1.50  # note (3)
INTEGRATED_LAUNDRY_EXTRA_M2 = 1.0  # note (4)
BEDROOM_CIRCULATION_REDUCTION = 0.20  # note (1): up to 20 % less, under conditions

TABLE_8_QUOTE = """\
Tabla 8. Figuras inscribibles mínimas (m)
Figura libre de obstáculos: Estar Ø1,20 (1); Comedor Ø1,20; Cocina Ø1,20; Dormitorio Ø1,20 (2); Baño Ø1,20 (3); Lavadero Ø1,20
Figura para mobiliario: Estar 2,50 x 3,00 o 2,80 x 2,80; Comedor Ø 2,50 o 2,30 x 3,00 (4); Cocina 1,00 m libre delante de la bancada en toda su longitud; Dormitorio Principal: 2,60 x 2,60, Doble: 2,00 x 2,60 o 4,10 x 1,80, Sencillo: 2,00 x 2,00; Baño Ver Tabla 10; Lavadero Ver tabla 11
(1) En la zona de acceso a la vivienda se cumplirá también esta figura.
(2) Al menos un dormitorio doble se podrá inscribir esta figura.
(3) Al menos un baño se podrá inscribir esta figura.
(4) El rectángulo de 2,30 x 3,00 se admitirá como figura alternativa en el caso de que el comedor esté combinado con otros espacios y el lado menor del recinto resultante tenga una dimensión mínima de 2,50 m.
"""

FREE_CIRCLE_DIAMETER_M = 1.20
STAR_RECTS = ((2.50, 3.00), (2.80, 2.80))
DINING_CIRCLE_DIAMETER_M = 2.50
DINING_RECT = (2.30, 3.00)
DINING_RECT_MIN_SIDE_M = 2.50
BEDROOM_MAIN_RECT = (2.60, 2.60)
BEDROOM_DOUBLE_RECTS = ((2.00, 2.60), (4.10, 1.80))
BEDROOM_SINGLE_RECT = (2.00, 2.00)
