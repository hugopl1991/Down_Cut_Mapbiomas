import argparse
import logging
from pathlib import Path

import geopandas as gpd
import rasterio
import requests
from rasterio.mask import mask
from tqdm import tqdm


BASE_URL = (
    "https://storage.googleapis.com/mapbiomas-public/"
    "initiatives/brasil/collection11/lulc/coverage/"
    "brazil_coverage/brazil_coverage-col11_{year}.tif"
)

DEFAULT_YEARS = range(1985, 2026)
DEFAULT_STATES = [
    "AM_Mapbiomas",
    "BA_Mapbiomas",
    "ES_Mapbiomas",
    "MA_Mapbiomas",
    "MG_Mapbiomas",
    "PA_Mapbiomas",
    "RJ_Mapbiomas",
    "SP_Mapbiomas",
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def ensure_directories(*dirs: Path) -> None:
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)


def download_raster(year: int, download_dir: Path, base_url: str = BASE_URL) -> Path:
    """Baixa o raster nacional do MapBiomas para um ano específico."""
    filename = f"mapbiomas_col11_Brazil_{year}.tif"
    output_path = download_dir / filename

    if output_path.exists():
        logging.info("[OK] Raster já existe: %s", filename)
        return output_path

    url = base_url.format(year=year)
    logging.info("[DOWNLOAD] Ano %s - %s", year, url)

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0) or 0)

    with output_path.open("wb") as file, tqdm(
        total=total_size or None,
        unit="B",
        unit_scale=True,
        desc=f"Baixando {year}",
        leave=False,
    ) as progress:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)
                progress.update(len(chunk))

    return output_path


def clip_raster(raster_path: Path, shapefile_path: Path, output_path: Path) -> Path:
    """Recorta um raster usando o shapefile informado."""
    with rasterio.open(raster_path) as src:
        shape = gpd.read_file(shapefile_path)

        if shape.empty:
            raise ValueError(f"Shapefile vazio: {shapefile_path}")

        if shape.crs is None:
            raise ValueError(f"Shapefile sem CRS definido: {shapefile_path}")

        if shape.crs != src.crs:
            shape = shape.to_crs(src.crs)

        valid_geometries = shape[shape.geometry.notna() & ~shape.geometry.is_empty]

        if valid_geometries.empty:
            raise ValueError(f"Nenhuma geometria válida em: {shapefile_path}")

        clipped, transform = mask(
            src,
            valid_geometries.geometry.values,
            crop=True,
            all_touched=True,
        )

        profile = src.profile.copy()
        profile.update(
            {
                "height": clipped.shape[1],
                "width": clipped.shape[2],
                "transform": transform,
                "compress": "lzw",
            }
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(clipped)
            if src.descriptions:
                dst.descriptions = src.descriptions

    return output_path


def process_year(
    year: int,
    states: list[str],
    shape_dir: Path,
    output_dir: Path,
    download_dir: Path,
) -> None:
    """Processa um ano completo: baixa o raster nacional e recorta por estado."""
    raster_path = download_raster(year, download_dir)
    logging.info("\n[PROCESSANDO] Ano %s", year)

    for state in states:
        shapefile_path = shape_dir / f"{state}.shp"
        if not shapefile_path.exists():
            logging.warning("[AVISO] Shapefile não encontrado: %s", shapefile_path)
            continue

        state_dir = output_dir / state
        ensure_directories(state_dir)

        output_path = state_dir / f"mapbiomas_col11_{state}_{year}.tif"
        if output_path.exists():
            logging.info("[OK] %s %s já processado", state, year)
            continue

        logging.info("[CLIP] %s - %s", state, year)
        try:
            clip_raster(raster_path, shapefile_path, output_path)
            logging.info("[OK] %s", output_path)
        except Exception as exc:  # pragma: no cover - logging is enough
            logging.error("[ERRO] %s - %s: %s", state, year, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa e recorta os rasters do MapBiomas por estado."
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=list(DEFAULT_YEARS),
        help="Anos a serem processados. Ex.: --years 1985 1990 2020",
    )
    parser.add_argument(
        "--states",
        nargs="+",
        default=DEFAULT_STATES,
        help="Estados/arquivos .shp a processar. Ex.: --states AM_Mapbiomas SP_Mapbiomas",
    )
    parser.add_argument(
        "--shape-dir",
        type=Path,
        default=Path("Shape_estados"),
        help="Diretório com os shapefiles dos estados.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("dados/downloads"),
        help="Diretório para salvar os rasters nacionais baixados.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados/estados"),
        help="Diretório de saída para os rasters recortados.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories(args.download_dir, args.output_dir, args.shape_dir)

    for year in args.years:
        try:
            process_year(
                year=year,
                states=args.states,
                shape_dir=args.shape_dir,
                output_dir=args.output_dir,
                download_dir=args.download_dir,
            )
        except Exception as exc:
            logging.error("[ERRO GERAL] Ano %s: %s", year, exc)


if __name__ == "__main__":
    main()