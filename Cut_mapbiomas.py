import argparse
import logging
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.mask import mask


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


def clip_raster(raster_path: Path, shapefile_path: Path, output_path: Path) -> Path:
    """Recorta um raster nacional por um shapefile de estado."""
    with rasterio.open(raster_path) as src:
        shape = gpd.read_file(shapefile_path)

        if shape.empty:
            raise ValueError(f"Shapefile vazio: {shapefile_path}")

        if shape.crs is None:
            raise ValueError(f"Shapefile sem CRS definido: {shapefile_path}")

        if shape.crs != src.crs:
            shape = shape.to_crs(src.crs)

        valid_shape = shape[shape.geometry.notna() & ~shape.geometry.is_empty]
        if valid_shape.empty:
            raise ValueError(f"Nenhuma geometria válida em: {shapefile_path}")

        clipped, transform = mask(
            src,
            valid_shape.geometry.values,
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
    raster_dir: Path,
    shape_dir: Path,
    output_dir: Path,
) -> None:
    """Processa os rasters nacionais de um ano, recortando para cada estado."""
    raster_name = f"mapbiomas_col11_Brazil_{year}.tif"
    raster_path = raster_dir / raster_name

    if not raster_path.exists():
        logging.warning("[AVISO] Raster não encontrado: %s", raster_path)
        return

    logging.info("\n%s", "=" * 70)
    logging.info("PROCESSANDO ANO: %s", year)
    logging.info("%s", "=" * 70)

    for state_name in states:
        shapefile_path = shape_dir / f"{state_name}.shp"
        if not shapefile_path.exists():
            logging.warning("[AVISO] Shapefile não encontrado: %s", shapefile_path)
            continue

        state_code = state_name.split("_")[0]
        output_name = f"mapbiomas_col11_{state_code}_{year}.tif"
        output_path = output_dir / output_name

        if output_path.exists():
            logging.info("[EXISTE] %s", output_name)
            continue

        logging.info("[CLIP] %s - %s", state_code, year)
        try:
            clip_raster(raster_path, shapefile_path, output_path)
            logging.info("[OK] %s", output_name)
        except Exception as exc:
            logging.error("[ERRO] %s - %s: %s", state_code, year, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recorta rasters nacionais do MapBiomas por estado usando shapefiles locais."
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=list(DEFAULT_YEARS),
        help="Anos a processar. Ex.: --years 1985 1990 2020",
    )
    parser.add_argument(
        "--states",
        nargs="+",
        default=DEFAULT_STATES,
        help="Estados a processar. Ex.: --states AM_Mapbiomas SP_Mapbiomas",
    )
    parser.add_argument(
        "--raster-dir",
        type=Path,
        default=Path("dados/downloads"),
        help="Diretório com os rasters nacionais baixados.",
    )
    parser.add_argument(
        "--shape-dir",
        type=Path,
        default=Path("Shape_estados"),
        help="Diretório com os shapefiles dos estados.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados/estados"),
        help="Diretório para salvar os rasters recortados.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.shape_dir.mkdir(parents=True, exist_ok=True)

    for year in args.years:
        try:
            process_year(
                year=year,
                states=args.states,
                raster_dir=args.raster_dir,
                shape_dir=args.shape_dir,
                output_dir=args.output_dir,
            )
        except Exception as exc:
            logging.error("[ERRO GERAL] Ano %s: %s", year, exc)


if __name__ == "__main__":
    main()