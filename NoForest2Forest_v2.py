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
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ======================================================
# CONFIGURAÇÕES DA ANÁLISE
# ======================================================
#ESTADOS = ["AM", "PA", "MA", "BA", "MG", "RJ", "SP", "ES"]
ESTADOS = [ "MA"]

# Definir o intervalo de anos (ex: 1985 até 2024)
ANOS = list(range(1985, 2025)) 

PASTA_RASTER = Path("dados/estados")
PASTA_SHAPE = Path("Shape_estados/AIO")

# Pasta para salvar os rasters gerados (ano a ano)
PASTA_SAIDA_RASTERS = Path("Rasters_Transicao_Anual")
PASTA_SAIDA_RASTERS.mkdir(exist_ok=True)

ARQUIVO_SAIDA = "transicao_nao_floresta_para_floresta_anual.csv"

# ======================================================
# DEFINIÇÃO DAS CLASSES DE TRANSIÇÃO
# ======================================================
CLASSES_ORIGEM = {
    # Vegetação natural não florestal
    #12, 29, 32, 77, 84, 11, 50,
    # Agropecuária
    #9, 15, 18, 19, 20, 21, 35, 36, 39, 40, 41, 46, 47, 48, 62,
    # Área não vegetada
    23, #24, 25, 30, 75, 91
}

CLASSES_DESTINO = {
    # Floresta
    3, 4, 5, 6, 7, 49
}

# ======================================================
# PROCESSAMENTO
# ======================================================
resultados = []

for estado in ESTADOS:
    shp_file = PASTA_SHAPE / f"ADAIMO_2025_{estado}.shp"

    if not shp_file.exists():
        continue

    gdf = gpd.read_file(shp_file)
    gdf = gdf[gdf.geometry.notnull() & gdf.is_valid]

    if len(gdf) == 0:
        continue
        
    # ==================================================
    # LOOP ANO A ANO
    # ==================================================
    for i in range(len(ANOS) - 1):
        ano_ini = ANOS[i]
        ano_fim = ANOS[i + 1]

        logging.info(f"Processando Estado: {estado} | Comparando {ano_ini} com {ano_fim}")

        raster_inicial_path = PASTA_RASTER / f"mapbiomas_col11_{estado}_{ano_ini}.tif"
        raster_final_path = PASTA_RASTER / f"mapbiomas_col11_{estado}_{ano_fim}.tif"

        if not (raster_inicial_path.exists() and raster_final_path.exists()):
            logging.warning(f"Rasters ausentes para {estado} nos anos {ano_ini}-{ano_fim}.")
            continue

        try:
            with rasterio.open(raster_inicial_path) as src_ini, rasterio.open(raster_final_path) as src_fim:
                
                # Garantir mesmo CRS
                gdf_proc = gdf.to_crs(src_ini.crs) if src_ini.crs != gdf.crs else gdf
                
                # Resolução do pixel (MapBiomas geralmente é 30x30m)
                pixel_area_ha = (src_ini.res[0] * src_ini.res[1]) / 10000

                for idx, row in enumerate(gdf_proc.itertuples()):
                    try:
                        # Clip e captura do transform
                        clip_ini, transform_ini = mask(src_ini, [row.geometry], crop=True)
                        clip_fim, _ = mask(src_fim, [row.geometry], crop=True)
                        
                        dados_ini = clip_ini[0]
                        dados_fim = clip_fim[0]
                        
                        if dados_ini.shape != dados_fim.shape:
                            logging.warning(f"Dimensões diferentes no clip da operação {getattr(row, 'Opunit', idx)}")
                            continue

                        # Criar máscaras booleanas para as transições
                        mask_origem = np.isin(dados_ini, list(CLASSES_ORIGEM))
                        mask_destino = np.isin(dados_fim, list(CLASSES_DESTINO))
                        
                        # Interseção: era não-floresta no inicio E é floresta no final
                        mask_transicao = mask_origem & mask_destino
                        
                        # Contar pixels e calcular área
                        pixels_mudanca = np.sum(mask_transicao)
                        
                        if pixels_mudanca > 0:
                            area_ha = pixels_mudanca * pixel_area_ha
                            op_unit = getattr(row, "Opunit", f"geom_{idx}")
                            
                            # Adicionando os anos no CSV para rastreabilidade
                            resultados.append({
                                "Estado": estado,
                                "Ano_Inicial": ano_ini,
                                "Ano_Final": ano_fim,
                                "Opunit": op_unit,
                                "Structure": getattr(row, "Structure", None),
                                "Management": getattr(row, "Management", None),
                                "Pixels_Alterados": pixels_mudanca,
                                "Area_Mudanca_ha": round(area_ha, 2)
                            })

                            # ==================================================
                            # CRIAÇÃO DO RASTER DE SAÍDA (ÁREAS ALTERADAS)
                            # ==================================================
                            out_image = np.where(mask_transicao, 1, 0).astype(rasterio.uint8)
                            out_image = np.expand_dims(out_image, axis=0)

                            out_meta = src_ini.meta.copy()
                            out_meta.update({
                                "driver": "GTiff",
                                "height": out_image.shape[1],
                                "width": out_image.shape[2],
                                "transform": transform_ini,
                                "dtype": rasterio.uint8,
                                "nodata": 0,
                                "count": 1,
                                "compress": "lzw"
                            })

                            # Nome do arquivo agora inclui os anos comparados
                            nome_arquivo_raster = PASTA_SAIDA_RASTERS / f"transicao_{estado}_{op_unit}_{ano_ini}_{ano_fim}.tif"
                            
                            with rasterio.open(nome_arquivo_raster, "w", **out_meta) as dest:
                                dest.write(out_image)
                                
                            logging.info(f"Raster gerado: {nome_arquivo_raster.name}")

                    except Exception as erro:
                        logging.error(f"Erro na geometria {getattr(row,'Opunit',idx)} ({ano_ini}-{ano_fim}): {erro}")

        except Exception as erro:
            logging.error(f"Erro ao abrir rasters de {estado} ({ano_ini}-{ano_fim}): {erro}")

# ======================================================
# EXPORTAR RESULTADO TABULAR
# ======================================================
if resultados:
    df = pd.DataFrame(resultados)
    df = df.sort_values(["Estado", "Ano_Inicial", "Opunit"])
    df.to_csv(ARQUIVO_SAIDA, sep=";", index=False)
    logging.info(f"Concluído! Arquivo gerado: {ARQUIVO_SAIDA} com {len(df)} registros de transição.")
else:
    logging.info("Nenhuma transição encontrada nos parâmetros especificados.")