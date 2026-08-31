import os
import requests
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from tqdm import tqdm


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_URL = (
    "https://storage.googleapis.com/mapbiomas-public/"
    "initiatives/brasil/collection11/lulc/coverage/"
    "brazil_coverage/brazil_coverage-col11_{year}.tif"
)

DOWNLOAD_DIR = "dados/downloads"
OUTPUT_DIR = "dados/estados"
SHAPE_DIR = "Shape_estados"

ANOS = range(1985, 2026)

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

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# DOWNLOAD
# ============================================================

def download_raster(year):
    """
    Baixa o raster nacional do MapBiomas para determinado ano.
    """

    filename = f"brazil_coverage-col11_{year}.tif"
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    url = BASE_URL.format(year=year)

    if os.path.exists(output_path):
        print(f"[OK] Raster já existe: {filename}")
        return output_path

    print(f"[DOWNLOAD] Ano {year}")
    print(url)

    response = requests.get(
        url,
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))

    with open(output_path, "wb") as file:

        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=f"Baixando {year}"
        ) as progress:

            for chunk in response.iter_content(chunk_size=1024 * 1024):

                if chunk:

                    file.write(chunk)
                    progress.update(len(chunk))

    return output_path


# ============================================================
# RECORTE
# ============================================================

def clip_raster(raster_path, shapefile_path, output_path):

    with rasterio.open(raster_path) as src:

        shape = gpd.read_file(shapefile_path)

        # Garantir que o shapefile esteja no mesmo CRS
        # do raster
        shape = shape.to_crs(src.crs)

        geometries = shape.geometry.values

        clipped, transform = mask(
            src,
            geometries,
            crop=True,
            all_touched=True
        )

        profile = src.profile.copy()

        profile.update({
            "height": clipped.shape[1],
            "width": clipped.shape[2],
            "transform": transform,
            "compress": "lzw"
        })

        with rasterio.open(output_path, "w", **profile) as dst:

            dst.write(clipped)


# ============================================================
# PROCESSAMENTO DE UM ANO
# ============================================================

def process_year(year):

    raster_path = download_raster(year)

    print(f"\n[PROCESSANDO] Ano {year}")

    for estado in ESTADOS:

        shapefile = os.path.join(
            SHAPE_DIR,
            f"{estado}.shp"
        )

        estado_dir = os.path.join(
            OUTPUT_DIR,
            estado
        )

        os.makedirs(
            estado_dir,
            exist_ok=True
        )

        output_path = os.path.join(
            estado_dir,
            f"{estado}_{year}.tif"
        )

        if os.path.exists(output_path):

            print(
                f"[OK] {estado} {year} já processado"
            )

            continue

        print(
            f"[CLIP] {estado} - {year}"
        )

        clip_raster(
            raster_path,
            shapefile,
            output_path
        )

        print(
            f"[OK] {output_path}"
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
                f"[ERRO] Ano {ano}: {e}"
            )