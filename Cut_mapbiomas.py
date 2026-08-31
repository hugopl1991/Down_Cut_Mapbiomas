import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Diretório onde estão os rasters nacionais já baixados
RASTER_DIR = "dados/downloads"

# Diretório dos shapefiles
SHAPE_DIR = "Shape_estados"

# Diretório de saída
OUTPUT_DIR = "dados/estados"

# Anos a processar
ANOS = range(1985, 2026)

# Shapefiles dos estados
ESTADOS = [
    "AM_Mapbiomas",
    "BA_Mapbiomas",
    "ES_Mapbiomas",
    "MA_Mapbiomas",
    "MG_Mapbiomas",
    "PA_Mapbiomas",
    "RJ_Mapbiomas",
    "SP_Mapbiomas",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# RECORTE DO RASTER
# ============================================================

def clip_raster(raster_path, shapefile_path, output_path):

    with rasterio.open(raster_path) as src:

        # ----------------------------------------------------
        # Ler shapefile
        # ----------------------------------------------------

        shape = gpd.read_file(shapefile_path)

        # ----------------------------------------------------
        # Verificar CRS
        # ----------------------------------------------------

        if shape.crs is None:
            raise ValueError(
                f"Shapefile sem CRS definido: {shapefile_path}"
            )

        # Reprojetar somente para o CRS do raster
        if shape.crs != src.crs:
            shape = shape.to_crs(src.crs)

        # ----------------------------------------------------
        # Remover geometrias vazias
        # ----------------------------------------------------

        shape = shape[
            shape.geometry.notna()
            & ~shape.geometry.is_empty
        ]

        geometries = shape.geometry.values

        if len(geometries) == 0:
            raise ValueError(
                f"Nenhuma geometria válida em: {shapefile_path}"
            )

        # ----------------------------------------------------
        # RECORTE
        #
        # all_touched=True:
        # inclui todo pixel que tiver contato com a máscara.
        # ----------------------------------------------------

        clipped, transform = mask(
            src,
            geometries,
            crop=True,
            all_touched=True
        )

        # ----------------------------------------------------
        # Atualizar perfil mantendo as propriedades originais
        # ----------------------------------------------------

        profile = src.profile.copy()

        profile.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=transform,
            compress="lzw"
        )

        # ----------------------------------------------------
        # Salvar
        # ----------------------------------------------------

        with rasterio.open(
            output_path,
            "w",
            **profile
        ) as dst:

            dst.write(clipped)

            # Preservar descrição das bandas
            if src.descriptions:
                dst.descriptions = src.descriptions

    return output_path


# ============================================================
# PROCESSAMENTO DE UM ANO
# ============================================================

def process_year(year):

    # --------------------------------------------------------
    # Raster nacional
    # --------------------------------------------------------

    raster_name = (
        f"brazil_coverage-col11_{year}.tif"
    )

    raster_path = os.path.join(
        RASTER_DIR,
        raster_name
    )

    if not os.path.exists(raster_path):

        print(
            f"[AVISO] Raster não encontrado: "
            f"{raster_path}"
        )

        return

    print()
    print("=" * 70)
    print(f"PROCESSANDO ANO: {year}")
    print("=" * 70)

    # --------------------------------------------------------
    # Processar estados
    # --------------------------------------------------------

    for estado_nome in ESTADOS:

        # ----------------------------------------------------
        # Shapefile
        # ----------------------------------------------------

        shapefile_path = os.path.join(
            SHAPE_DIR,
            f"{estado_nome}.shp"
        )

        if not os.path.exists(shapefile_path):

            print(
                f"[AVISO] Shapefile não encontrado: "
                f"{shapefile_path}"
            )

            continue

        # ----------------------------------------------------
        # Extrair sigla
        #
        # AM_Mapbiomas -> AM
        # BA_Mapbiomas -> BA
        # PA_Mapbiomas -> PA
        # ----------------------------------------------------

        sigla = estado_nome.split("_")[0]

        # ----------------------------------------------------
        # Nome final
        # ----------------------------------------------------

        output_name = (
            f"mapbiomas_col11_{sigla}_{year}.tif"
        )

        output_path = os.path.join(
            OUTPUT_DIR,
            output_name
        )

        # ----------------------------------------------------
        # Se já existe, não processar novamente
        # ----------------------------------------------------

        if os.path.exists(output_path):

            print(
                f"[EXISTE] {output_name}"
            )

            continue

        # ----------------------------------------------------
        # Recorte
        # ----------------------------------------------------

        print(
            f"[CLIP] {sigla} - {year}"
        )

        try:

            clip_raster(
                raster_path,
                shapefile_path,
                output_path
            )

            print(
                f"[OK] {output_name}"
            )

        except Exception as e:

            print(
                f"[ERRO] {sigla} - {year}: {e}"
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    for ano in ANOS:

        try:

            process_year(ano)

        except Exception as e:

            print(
                f"[ERRO GERAL] Ano {ano}: {e}"
            )