# Down_Cut_Mapbiomas

Este projeto automatiza o download e o recorte dos rasters de cobertura e uso do solo do MapBiomas para diferentes estados brasileiros.

A ideia principal é:

- baixar o raster nacional do MapBiomas para um ano específico;
- localizar o shapefile do estado desejado;
- recortar o raster para a geometria do estado;
- salvar o resultado em uma pasta organizada por estado e ano.

## O que o projeto faz

- `Down_cut.py`: baixa o raster nacional do MapBiomas e recorta automaticamente cada estado informado.
- `Cut_mapbiomas.py`: recorta rasters nacionais já baixados sem realizar novo download.
- `Avaliacao.py`: avalia os rasters recortados por unidade geográfica, identifica as classes MapBiomas válidas e exporta um CSV com resumo por ano, estado e atributos da operação.
- `Shape_estados/`: pasta com os shapefiles dos estados brasileiros.
- `Shape_estados/AIO/`: shapefiles das áreas de interesse/operacionais usados na avaliação.
- `dados/downloads/`: armazenamento dos rasters nacionais baixados.
- `dados/estados/`: saída dos rasters recortados por estado.

## Requisitos

- Python 3.10 ou superior
- `geopandas`
- `rasterio`
- `requests`
- `tqdm`

Instale as dependências com:

```bash
pip install geopandas rasterio requests tqdm
```

Se preferir, também pode criar um ambiente virtual antes da instalação:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install geopandas rasterio requests tqdm
```

## Estrutura do projeto

```text
Down_Cut_Mapbiomas/
├── Down_cut.py
├── Cut_mapbiomas.py
├── Avaliacao.py
├── README.md
├── Shape_estados/
│   ├── AM_Mapbiomas.shp
│   ├── BA_Mapbiomas.shp
│   ├── SP_Mapbiomas.shp
│   ├── AIO/
│   │   ├── ADAIMO_2025_AM.shp
│   │   └── ...
│   └── ...
├── dados/
│   ├── downloads/
│   ├── estados/
│   └── classes_mapbiomas_ADAIMO_1985_2025.csv
└── ...
```

## Como usar

### 1) Baixar e recortar em um único passo

Este comando baixa os rasters nacionais para os anos informados e recorta para cada estado listado:

```bash
python Down_cut.py --years 2020 2021 --states AM_Mapbiomas SP_Mapbiomas
```

Parâmetros disponíveis:

- `--years`: anos a processar
- `--states`: nomes dos shapefiles dos estados
- `--shape-dir`: diretório com os shapefiles
- `--download-dir`: pasta para salvar os rasters nacionais
- `--output-dir`: pasta para salvar os rasters recortados

Exemplo com diretórios personalizados:

```bash
python Down_cut.py --years 2020 2021 --states AM_Mapbiomas BA_Mapbiomas --shape-dir Shape_estados --download-dir dados/downloads --output-dir dados/estados
```

### 2) Recortar rasters já baixados

Se os rasters nacionais já estiverem presentes na pasta `dados/downloads`, use:

```bash
python Cut_mapbiomas.py --years 2020 2021 --states AM_Mapbiomas SP_Mapbiomas
```

Exemplo com parâmetros explícitos:

```bash
python Cut_mapbiomas.py --years 1985 1990 --states AM_Mapbiomas MG_Mapbiomas --raster-dir dados/downloads --shape-dir Shape_estados --output-dir dados/estados
```

### 3) Avaliar classes MapBiomas por operação/estado

O script `Avaliacao.py` usa os rasters recortados e os shapefiles da pasta `Shape_estados/AIO` para calcular, para cada unidade geográfica, quais classes MapBiomas válidas aparecem em cada ano.

Ele gera um CSV final no formato:

```bash
python Avaliacao.py
```

Arquivo gerado:

```text
classes_mapbiomas_ADAIMO_1985_2025.csv
```

Colunas principais do CSV:

- `Ano`
- `Estado`
- `Opunit`
- `Structure`
- `Management`
- `Classe_ID`

Esse arquivo é útil para comparar a presença de classes do MapBiomas por operação, estrutura e manejo ao longo do tempo.

## Nome dos arquivos gerados

Os rasters recortados seguem o padrão:

```text
mapbiomas_col11_UF_ano.tif
```

Exemplo:

```text
mapbiomas_col11_AM_2020.tif
mapbiomas_col11_SP_2021.tif
```

## Exemplo de saída

```text
INFO: [DOWNLOAD] Ano 2020 - https://storage.googleapis.com/...
INFO: [CLIP] AM - 2020
INFO: [OK] mapbiomas_col11_AM_2020.tif
```

## Observações importantes

- O script compara o CRS do shapefile com o CRS do raster e reprojecta automaticamente quando necessário.
- Arquivos já existentes não são reprocessados.
- Caso o raster ou o shapefile não exista, o sistema registra um aviso e continua o processamento.
- Os shapefiles devem ter nomes compatíveis com os valores passados em `--states`, como `AM_Mapbiomas.shp`.

## Dicas de uso

- Use apenas os anos realmente necessários para economizar tempo e espaço em disco.
- Verifique se os shapefiles estão na pasta `Shape_estados` e que os nomes batem com os estados informados.
- Para grandes volumes de dados, é recomendável rodar por blocos de anos ou estados.
- Em caso de erro em um estado específico, o processamento continua para os demais.

## Casos de uso comuns

- Download e recorte de uma única região para um ano específico.
- Processamento de vários anos para uma lista de estados.
- Geração de rasters prontos para análise em SIG ou modelagem.

## Licença e fontes

Este projeto utiliza dados e produtos do MapBiomas. Consulte a documentação oficial do MapBiomas para detalhes sobre uso, políticas e limitações de dados.
