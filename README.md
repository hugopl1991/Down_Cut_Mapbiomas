# Down_Cut_Mapbiomas

Scripts para baixar e recortar rasters do MapBiomas para estados brasileiros.

## Estrutura

- `Down_cut.py`: baixa o raster nacional do MapBiomas por ano e recorta para cada estado usando um shapefile correspondente.
- `Cut_mapbiomas.py`: recorta rasters nacionais já baixados para cada estado.
- `Shape_estados/`: diretório com os shapefiles dos estados.
- `dados/downloads/`: armazenamento dos rasters nacionais.
- `dados/estados/`: saída dos rasters recortados.

## Requisitos

- Python 3.10+
- `geopandas`
- `rasterio`
- `requests`
- `tqdm`

Instale as dependências com:

```bash
pip install geopandas rasterio requests tqdm
```

## Como usar

### 1) Baixar e recortar em um único passo

```bash
python Down_cut.py --years 2020 2021 --states AM_Mapbiomas SP_Mapbiomas
```

Parâmetros opcionais:

- `--years`: anos para processar
- `--states`: nomes dos arquivos shapefile a processar
- `--shape-dir`: diretório dos shapefiles
- `--download-dir`: diretório de download
- `--output-dir`: diretório de saída

### 2) Recortar rasters já baixados

```bash
python Cut_mapbiomas.py --years 2020 2021 --states AM_Mapbiomas SP_Mapbiomas
```

## Exemplo de saída

```text
INFO: [DOWNLOAD] Ano 2020 - https://...
INFO: [CLIP] AM_Mapbiomas - 2020
INFO: [OK] dados/estados/AM_Mapbiomas/mapbiomas_col11_AM_2020.tif
```

## Observações

- O script usa o CRS do raster para reprojetar os shapefiles antes do recorte.
- Arquivos já existentes não são reprocessados.
- Caso o raster ou o shapefile não exista, o script avisa no log e continua.

## Dicas

- Use `--years` apenas para os anos necessários para economizar tempo e espaço em disco.
- Verifique se a pasta `Shape_estados` contém os arquivos com o mesmo nome dos estados informados no parâmetro `--states`.
