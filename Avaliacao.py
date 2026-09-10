from pathlib import Path
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask

# ======================================================
# LOG
# ======================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ======================================================
# CONFIGURAÇÕES
# ======================================================

ESTADOS = [
    "AM",
    "PA",
    "MA",
    "BA",
    "MG",
    "RJ",
    "SP",
    "ES"
]

ANOS = range(1985, 2026)

PASTA_RASTER = Path("dados/estados")
PASTA_SHAPE = Path("Shape_estados/AIO")

ARQUIVO_SAIDA = "classes_mapbiomas_ADAIMO_1985_2025.csv"

# ======================================================
# CLASSES OFICIAIS MAPBIOMAS COLEÇÃO 11
# ======================================================

CLASSES_VALIDAS = {
    # Floresta
    3, 4, 5, 6, 7, 49,

    # Vegetação natural não florestal
    11, 12, 29, 32, 50, 77, 84,

    # Agropecuária
    9, 15, 18, 19, 20, 21,
    35, 36, 39, 40, 41,
    46, 47, 48, 62,

    # Área não vegetada
    23, 24, 25, 30, 75, 91,

    # Água
    31, 33
}

# ======================================================
# RESULTADO
# ======================================================

resultado = set()

# ======================================================
# LOOP DOS ESTADOS
# ======================================================

for estado in ESTADOS:

    shp_file = (
        PASTA_SHAPE /
        f"ADAIMO_2025_{estado}.shp"
    )

    if not shp_file.exists():
        logging.warning(
            f"Shapefile não encontrado: {shp_file}"
        )
        continue

    logging.info(f"Estado: {estado}")

    gdf = gpd.read_file(shp_file)

    # Remove geometrias problemáticas
    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[gdf.is_valid]

    if len(gdf) == 0:
        logging.warning(
            f"Sem geometrias válidas para {estado}"
        )
        continue

    # ==================================================
    # LOOP DOS ANOS
    # ==================================================

    for ano in ANOS:

        raster_file = (
            PASTA_RASTER /
            f"mapbiomas_col11_{estado}_{ano}.tif"
        )

        if not raster_file.exists():

            logging.warning(
                f"Raster ausente: "
                f"{raster_file.name}"
            )

            continue

        logging.info(
            f"Processando {estado} - {ano}"
        )

        try:

            with rasterio.open(
                raster_file
            ) as src:

                if src.crs != gdf.crs:
                    gdf_proc = gdf.to_crs(
                        src.crs
                    )
                else:
                    gdf_proc = gdf

                nodata = src.nodata

                for row in gdf_proc.itertuples():

                    try:

                        clip, _ = mask(
                            src,
                            [row.geometry],
                            crop=True
                        )

                        dados = clip[0]

                        # Remove NoData
                        if nodata is not None:

                            dados = dados[
                                dados != nodata
                            ]

                        # Remove NaN
                        dados = dados[
                            ~np.isnan(dados)
                        ]

                        if dados.size == 0:
                            continue

                        # Classes únicas
                        classes = np.unique(
                            dados
                        )

                        # Mantém apenas
                        # classes oficiais
                        classes = [
                            int(c)
                            for c in classes
                            if int(c) in
                            CLASSES_VALIDAS
                        ]

                        if len(classes) == 0:
                            continue

                        for classe in classes:

                            resultado.add(
                                (
                                    ano,
                                    estado,
                                    getattr(
                                        row,
                                        "Opunit",
                                        None
                                    ),
                                    getattr(
                                        row,
                                        "Structure",
                                        None
                                    ),
                                    getattr(
                                        row,
                                        "Management",
                                        None
                                    ),
                                    classe
                                )
                            )

                    except Exception as erro:

                        logging.error(
                            f"Erro "
                            f"{estado} | "
                            f"{ano} | "
                            f"{getattr(row,'Opunit',None)}"
                        )

                        logging.error(erro)

        except Exception as erro:

            logging.error(
                f"Erro ao abrir "
                f"{raster_file.name}"
            )

            logging.error(erro)

# ======================================================
# EXPORTAR RESULTADO
# ======================================================

df = pd.DataFrame(
    list(resultado),
    columns=[
        "Ano",
        "Estado",
        "Opunit",
        "Structure",
        "Management",
        "Classe_ID"
    ]
)

df = df.sort_values(
    [
        "Estado",
        "Opunit",
        "Ano",
        "Classe_ID"
    ]
)

df.to_csv(
    ARQUIVO_SAIDA,
    sep=";",
    index=False
)

logging.info(
    f"Concluído!"
)

logging.info(
    f"Registros: {len(df):,}"
)

logging.info(
    f"Arquivo: {ARQUIVO_SAIDA}"
)

# ======================================================
# RESUMO POR OPERAÇÃO
# ======================================================

resumo = (
    df.groupby(
        [
            "Estado",
            "Opunit"
        ]
    )["Classe_ID"]
    .apply(
        lambda x:
        ",".join(
            map(
                str,
                sorted(
                    x.unique()
                )
            )
        )
    )
    .reset_index()
)

resumo.rename(
    columns={
        "Classe_ID":
        "Classes_Encontradas"
    },
    inplace=True
)

resumo.to_csv(
    "Resumo_Classes_MapBiomas_por_Operacao.csv",
    sep=";",
    index=False
)

logging.info(
    "Resumo exportado com sucesso."
)