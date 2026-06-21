"""
Projeto: Painel DRX Argiloteca

Descrição:
Helpers for Argiloteca semantic enrichment of clay mineral metadata. Este modulo monta perfis autorizados de argilominerais a partir de vocabulario local, sementes Mindat e fontes complementares. A saida abastece paginas, subjects Invenio, comunidades e blocos de evidencia cientifica.

Autores:
- Alexandre Ribas Semeler
  E-mail: alexandre.semeler@ufrgs.br


Instituição:
Universidade Federal do Rio Grande do Sul (UFRGS)

Projeto:
Argiloteca / CPAA

Licença:
Preservar licença existente no repositório.

Última revisão:
2026-06-21

Observação:
Este arquivo integra o sistema de análise, comparação e interpretação de difratogramas de raios X para argilominerais.
"""

from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


MINDAT_SOURCE = "Mindat"
MINDAT_URI_PATTERN = re.compile(
    r"^https?://(?:www\.)?mindat\.org/min-(?P<id>\d+)\.html/?$",
    re.IGNORECASE,
)
ROOT_DIR = Path(__file__).resolve().parents[2]
CURATED_SEEDS_PATH = ROOT_DIR / "scripts" / "mineralogia" / "mindat_curated_seeds.json"
HANDBOOK_CURATED_PATH = ROOT_DIR / "scripts" / "mineralogia" / "handbook_curated_profiles.json"
SOURCE_CLAYS_CURATED_PATH = ROOT_DIR / "scripts" / "mineralogia" / "source_clays_curated_profiles.json"
REUSABLE_IMAGE_CURATED_PATH = ROOT_DIR / "scripts" / "mineralogia" / "reusable_image_curated_profiles.json"
VOCABULARY_PATH = ROOT_DIR / "app_data" / "data" / "vocabularies" / "argilominerais.jsonl"
GROUP_VOCABULARY_PATH = ROOT_DIR / "app_data" / "data" / "vocabularies" / "grupo_mineralogico.jsonl"
HANDBOOK_SOURCE = "Handbook of Mineralogy"
SOURCE_CLAYS_SOURCE = "Clay Minerals Society - Source Clays"
EARTHCHEM_SOURCE = "EarthChem"
HANDBOOK_PDF_BASE = "https://www.handbookofmineralogy.org/pdfs"
EARTHCHEM_HOME_URI = "https://earthchem.org/"
EARTHCHEM_PORTAL_URI = "https://portal.earthchem.org/"
EARTHCHEM_ACCESS_URI = "https://earthchem.org/data-access/overview"
EARTHCHEM_PETDB_URI = "https://earthchem.org/petdb"
EARTHCHEM_LEPR_URI = "https://lepr.earthchem.org/"
EARTHCHEM_EXPERIMENTAL_PETROLOGY_URI = "https://earthchem.org/communities/experimental-petrology"
EARTHCHEM_ECL_OVERVIEW_URI = "https://earthchem.org/ecl/submission-overview"
IMAGES_OF_CLAY_SOURCE = "Clay Minerals Society - Images of Clay"
IMAGES_OF_CLAY_URI = "https://www.minersoc.org/images-of-clay.html"
IMAGES_OF_CLAY_JUBILEE_URI = "https://www.minersoc.org/jubilee-year-2022.html"
IMAGES_OF_CLAY_LICENSE = (
    "Livre para download e uso sem fins lucrativos, com atribuicao obrigatoria ao Images of Clay Archive."
)
ARGILOTECA_SOURCE = "Argiloteca"
ARGILOTECA_COMMUNITY_PAGE = "/communities/{slug}/records?q=&l=list&p=1&s=10&sort=newest"
ARGILOTECA_TILE_LICENSE = "Uso interno curatorial na interface da Argiloteca."
NON_EMBEDDABLE_IMAGE_PATTERNS = (
    "mindat.org/xpic.php",
)

# Referencias visuais reutilizaveis por familia. Quando nao ha imagem exata
# incorporavel, o painel mostra uma imagem representativa com escopo explicito.
REUSABLE_IMAGE_FAMILY_REFERENCES = {
    "kaolin_group": {
        "source_name": "U.S. Geological Survey",
        "title": "Kaolinite Hill, Cuprite, Nevada, USA",
        "image_url": "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/IMG_2372_13.jpg",
        "page_url": "https://www.usgs.gov/media/images/kaolinite-hill",
        "license": "Public Domain.",
        "credit": "Photo by Lyle Mars via U.S. Geological Survey",
        "locality": "Cuprite, Nevada, USA",
        "provenance": "Imagem representativa do universo caulinitico, com dominio publico confirmado pela USGS.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do grupo caulinita-caulim.",
    },
    "smectite_group": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Saponite from the Isle of Skye, Scotland",
        "image_url": "https://www.minersoc.org/wp-content/uploads/2024/06/6-Jun-138-1359898_06-300x225.jpg",
        "page_url": IMAGES_OF_CLAY_JUBILEE_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Image courtesy Laura-Jane Strachan and Evelyne Delbos via Images of Clay Archive",
        "locality": "Isle of Skye, Scotland",
        "provenance": "Imagem representativa do grupo esmectita, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do grupo esmectita.",
    },
    "smectite_related": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Saponite from the Isle of Skye, Scotland",
        "image_url": "https://www.minersoc.org/wp-content/uploads/2024/06/6-Jun-138-1359898_06-300x225.jpg",
        "page_url": IMAGES_OF_CLAY_JUBILEE_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Image courtesy Laura-Jane Strachan and Evelyne Delbos via Images of Clay Archive",
        "locality": "Isle of Skye, Scotland",
        "provenance": "Micrografia representativa de material esmectitico relacionado, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa de material esmectitico relacionado.",
    },
    "illite_mica": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Chlorite and illite from the Images of Clay Archive",
        "image_url": "https://www.minersoc.org/wp-content/gallery/shimages/5-863094-c-chlorite-illite.jpg",
        "page_url": IMAGES_OF_CLAY_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Images of Clay Archive",
        "locality": "Clay Minerals Society and Mineralogical Society image archive",
        "provenance": "Micrografia representativa do eixo ilita-mica, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do eixo ilita-mica.",
    },
    "mica_group": {
        "source_name": ARGILOTECA_SOURCE,
        "title": "Imagem local da comunidade micas argilosas e ilitas",
        "image_url": "/static/images/community-tiles/micas-argilosas-ilitas-illite-usgs.jpg",
        "page_url": ARGILOTECA_COMMUNITY_PAGE.format(slug="micas-argilosas-ilitas"),
        "license": ARGILOTECA_TILE_LICENSE,
        "credit": "Curadoria visual local da Argiloteca",
        "locality": "Colecao tematica micas argilosas e ilitas",
        "provenance": "Imagem local da Argiloteca usada como referencia visual mais coerente para o grupo das micas argilosas.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Ainda nao foi confirmada uma imagem exata reutilizavel para este termo; a Argiloteca usa aqui uma imagem local representativa do grupo das micas argilosas e ilitas.",
    },
    "chlorite_group": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Chlorite (Sudoite) from the Images of Clay Archive",
        "image_url": "https://www.minersoc.org/wp-content/gallery/shimages/3-Gol_3902_c.jpg",
        "page_url": IMAGES_OF_CLAY_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Images of Clay Archive",
        "locality": "Clay Minerals Society and Mineralogical Society image archive",
        "provenance": "Micrografia representativa de clorita, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do grupo das cloritas.",
    },
    "chlorite_related": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Berthierine from Cornelian Bay, Scarborough, Yorkshire",
        "image_url": "https://www.minersoc.org/wp-content/uploads/2024/06/2-Feb-133-1356106_13-Berth-Cham-300x225.jpg",
        "page_url": IMAGES_OF_CLAY_JUBILEE_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Photo courtesy Evelyne Delbos via Images of Clay Archive",
        "locality": "Cornelian Bay, Scarborough, Yorkshire, England",
        "provenance": "Micrografia representativa de minerais cloriticos relacionados, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do eixo berthierina-clorita.",
    },
    "vermiculite_group": {
        "source_name": "U.S. Geological Survey",
        "title": "Vermiculite Attic Insulation Microscopic View",
        "image_url": "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/thumbnails/image/vermiculite_carousel.PNG",
        "page_url": "https://www.usgs.gov/media/images/vermiculite-attic-insulation-microscopic-view",
        "license": "Public Domain.",
        "credit": "Photo by Gregg A. Swayze via U.S. Geological Survey",
        "locality": "USGS microscopy reference image",
        "provenance": "Imagem representativa de vermiculita, com dominio publico confirmado pela USGS.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma micrografia representativa de vermiculita.",
    },
    "vermiculite_related": {
        "source_name": "U.S. Geological Survey",
        "title": "Vermiculite Attic Insulation Microscopic View",
        "image_url": "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/thumbnails/image/vermiculite_carousel.PNG",
        "page_url": "https://www.usgs.gov/media/images/vermiculite-attic-insulation-microscopic-view",
        "license": "Public Domain.",
        "credit": "Photo by Gregg A. Swayze via U.S. Geological Survey",
        "locality": "USGS microscopy reference image",
        "provenance": "Imagem representativa de materiais vermiculiticos relacionados, com dominio publico confirmado pela USGS.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma micrografia representativa do eixo vermiculita.",
    },
    "palygorskite_sepiolite_group": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Palygorskite from Berry and Branscombe West Cliffs, Devon",
        "image_url": "https://www.minersoc.org/wp-content/uploads/2024/06/8-Aug-140-1359891_06-300x225.jpg",
        "page_url": IMAGES_OF_CLAY_JUBILEE_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Image courtesy Evelyne Delbos and Laura-Jane Strachan via Images of Clay Archive",
        "locality": "Berry and Branscombe West Cliffs, Devon, England",
        "provenance": "Micrografia representativa do eixo paligorsquita-sepiolita, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do eixo paligorsquita-sepiolita.",
    },
    "serpentine_group": {
        "source_name": ARGILOTECA_SOURCE,
        "title": "Imagem local da comunidade caulim-serpentina",
        "image_url": "/static/images/community-tiles/caulim-serpentina-kaolinite-usgs.jpg",
        "page_url": ARGILOTECA_COMMUNITY_PAGE.format(slug="caulim-serpentina"),
        "license": ARGILOTECA_TILE_LICENSE,
        "credit": "Curadoria visual local da Argiloteca",
        "locality": "Colecao tematica caulim-serpentina",
        "provenance": "Imagem local da Argiloteca usada como referencia visual mais coerente para o grupo da serpentina.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Ainda nao foi confirmada uma imagem exata reutilizavel para este termo; a Argiloteca usa aqui uma imagem local representativa do grupo da serpentina.",
    },
    "pyrophyllite_talc": {
        "source_name": ARGILOTECA_SOURCE,
        "title": "Imagem local da comunidade pirofilita-talco",
        "image_url": "/static/images/community-tiles/pirofilita-talco-pyrophyllite.jpg",
        "page_url": ARGILOTECA_COMMUNITY_PAGE.format(slug="pirofilita-talco"),
        "license": ARGILOTECA_TILE_LICENSE,
        "credit": "Curadoria visual local da Argiloteca",
        "locality": "Colecao tematica pirofilita-talco",
        "provenance": "Imagem local da Argiloteca usada como referencia visual mais coerente para o eixo pirofilita-talco.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Ainda nao foi confirmada uma imagem exata reutilizavel para este termo; a Argiloteca usa aqui uma imagem local representativa do eixo pirofilita-talco.",
    },
    "pyrophyllite_talc_related": {
        "source_name": ARGILOTECA_SOURCE,
        "title": "Imagem local da comunidade pirofilita-talco",
        "image_url": "/static/images/community-tiles/pirofilita-talco-pyrophyllite.jpg",
        "page_url": ARGILOTECA_COMMUNITY_PAGE.format(slug="pirofilita-talco"),
        "license": ARGILOTECA_TILE_LICENSE,
        "credit": "Curadoria visual local da Argiloteca",
        "locality": "Colecao tematica pirofilita-talco",
        "provenance": "Imagem local da Argiloteca usada como referencia visual mais coerente para materiais relacionados ao eixo pirofilita-talco.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Ainda nao foi confirmada uma imagem exata reutilizavel para este termo; a Argiloteca usa aqui uma imagem local representativa do eixo pirofilita-talco.",
    },
    "short_range_order": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Microbotryoidal allophane from Hawks Wood mine, Cornwall",
        "image_url": "https://www.minersoc.org/wp-content/uploads/2024/06/10-Oct-142-1359901_12-300x225.jpg",
        "page_url": IMAGES_OF_CLAY_JUBILEE_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Image courtesy Laura-Jane Strachan via Images of Clay Archive",
        "locality": "Hawks Wood mine, Bodmin Moor, Cornwall, England",
        "provenance": "Micrografia representativa de materiais de ordem curta, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa do universo alofana-imogolita.",
    },
    "layered_double_hydroxide": {
        "source_name": ARGILOTECA_SOURCE,
        "title": "Imagem local da comunidade cloritas",
        "image_url": "/static/images/community-tiles/cloritas-chlorite.jpg",
        "page_url": ARGILOTECA_COMMUNITY_PAGE.format(slug="cloritas"),
        "license": ARGILOTECA_TILE_LICENSE,
        "credit": "Curadoria visual local da Argiloteca",
        "locality": "Colecao tematica cloritas",
        "provenance": "Imagem local da Argiloteca usada como referencia visual mais coerente para hidroxidos duplos lamelares do que o fallback comparativo anterior.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Ainda nao foi confirmada uma imagem exata reutilizavel para este termo; a Argiloteca usa aqui uma imagem local representativa de material lamelar hidratado.",
    },
    "mixed_layer": {
        "source_name": IMAGES_OF_CLAY_SOURCE,
        "title": "Illite-smectite from Woodbury Quarry, Worcestershire",
        "image_url": "https://www.minersoc.org/wp-content/uploads/2024/06/9-Sep-141-996735-42-300x225.jpg",
        "page_url": IMAGES_OF_CLAY_JUBILEE_URI,
        "license": IMAGES_OF_CLAY_LICENSE,
        "credit": "Image courtesy Laura-Jane Strachan via Images of Clay Archive",
        "locality": "Woodbury Quarry, Worcestershire, England",
        "provenance": "Micrografia representativa de argilominerais interestratificados, com licenca explicita para uso sem fins lucrativos.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Nao ha imagem exata reutilizavel confirmada para este termo; a Argiloteca usa aqui uma imagem representativa de argilomineral interestratificado.",
    },
    "phyllosilicate_related": {
        "source_name": ARGILOTECA_SOURCE,
        "title": "Imagem local da comunidade micas argilosas e ilitas",
        "image_url": "/static/images/community-tiles/micas-argilosas-ilitas-illite-usgs.jpg",
        "page_url": ARGILOTECA_COMMUNITY_PAGE.format(slug="micas-argilosas-ilitas"),
        "license": ARGILOTECA_TILE_LICENSE,
        "credit": "Curadoria visual local da Argiloteca",
        "locality": "Colecao tematica micas argilosas e ilitas",
        "provenance": "Imagem local da Argiloteca usada como referencia visual ampla para filossilicatos lamelares relacionados.",
        "scope_label": "Imagem representativa da familia mineralogica",
        "scope_note": "Ainda nao foi confirmada uma imagem exata reutilizavel para este termo; a Argiloteca usa aqui uma imagem local representativa de filossilicatos relacionados.",
    },
}

# Referencias Source Clays por familia. Elas sao comparativas quando nao ha
# padrao direto para a especie, para evitar sugerir equivalencia cientifica.
SOURCE_CLAYS_FAMILY_REFERENCES = {
    "kaolin_group": {
        "summary": "A Clay Minerals Society mantém materiais de referência clássicos de caulim bem e menos cristalino, úteis para comparar minerais do universo caulinítico.",
        "samples": [
            {
                "code": "KGa-1b",
                "label": "Kaolin low-defect",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Material de referência clássico para caulinita bem cristalizada."},
                ],
            },
            {
                "code": "KGa-2",
                "label": "Kaolin high-defect",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Material de referência clássico para caulinita mais desordenada."},
                ],
            },
        ],
    },
    "smectite_group": {
        "summary": "O repositório Source Clays oferece materiais de referência relevantes para o universo esmectítico, incluindo montmorilonitas sódicas e cálcicas, argila Cheto e hectorita sintética.",
        "samples": [
            {"code": "STx-1", "label": "Texas Montmorillonite", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
            {"code": "SWy-2", "label": "Na-Montmorillonite Wyoming", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
            {"code": "SAz-1", "label": "Cheto Smectite", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
            {"code": "SYnH-1", "label": "Synthetic Hectorite", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
            {"code": "SWa-1", "label": "Ferruginous Smectite", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "smectite_related": {
        "summary": "Materiais argilosos relacionados às esmectitas podem ser comparados com os padrões esmectíticos da Clay Minerals Society, especialmente SWy-2, STx-1 e SAz-1.",
        "samples": [
            {"code": "STx-1", "label": "Texas Montmorillonite", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
            {"code": "SWy-2", "label": "Na-Montmorillonite Wyoming", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
            {"code": "SAz-1", "label": "Cheto Smectite", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
        ],
    },
    "illite_mica": {
        "summary": "Para ilitas e micas argilosas, o Source Clays Repository oferece padrões clássicos de ilita e de material interestratificado ilita-esmectita.",
        "samples": [
            {"code": "IMt-1", "label": "Illite", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
            {"code": "IMt-2", "label": "Illite", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
            {"code": "ISMt-2", "label": "Illite-Smectite mixed layer", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "mica_group": {
        "summary": "Para ilitas e micas argilosas, o Source Clays Repository oferece padrões clássicos de ilita e de material interestratificado ilita-esmectita.",
        "samples": [
            {"code": "IMt-1", "label": "Illite", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
            {"code": "IMt-2", "label": "Illite", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
            {"code": "ISMt-2", "label": "Illite-Smectite mixed layer", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "chlorite_group": {
        "summary": "Para as cloritas, a Clay Minerals Society mantém como referência especial o material ripidolita CCa-2.",
        "samples": [
            {"code": "CCa-2", "label": "Ripidolite (Chlorite)", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "chlorite_related": {
        "summary": "Para as cloritas, a Clay Minerals Society mantém como referência especial o material ripidolita CCa-2.",
        "samples": [
            {"code": "CCa-2", "label": "Ripidolite (Chlorite)", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "vermiculite_group": {
        "summary": "Para vermiculitas e materiais relacionados, o acervo Source Clays inclui o padrão VTx-1 do Texas.",
        "samples": [
            {"code": "VTx-1", "label": "Vermiculite (Llano)", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "vermiculite_related": {
        "summary": "Para vermiculitas e materiais relacionados, o acervo Source Clays inclui o padrão VTx-1 do Texas.",
        "samples": [
            {"code": "VTx-1", "label": "Vermiculite (Llano)", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
    "palygorskite_sepiolite_group": {
        "summary": "O repositório Source Clays oferece o padrão PFl-1 como material de referência para argilominerais fibrosos do eixo paligorsquita-sepiolita.",
        "samples": [
            {"code": "PFl-1", "label": "Palygorskite (Attapulgite)", "facts": [{"label": "Tipo", "value": "Source Clay"}]},
        ],
    },
    "serpentine_group": {
        "summary": "A Clay Minerals Society não oferece um padrão direto de serpentina, mas mantém materiais comparativos Fe-Mg úteis para o estudo de minerais do universo serpentínico, especialmente CCa-2 e VTx-1.",
        "samples": [
            {
                "code": "CCa-2",
                "label": "Ripidolite (Chlorite)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Material comparativo Fe-Mg de alteração; não é um padrão direto de serpentina."},
                ],
            },
            {
                "code": "VTx-1",
                "label": "Vermiculite (Llano)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Material comparativo hidratado de alteração magnesiana; não é um padrão direto de serpentina."},
                ],
            },
        ],
    },
    "pyrophyllite_talc": {
        "summary": "A Clay Minerals Society não mantém um padrão direto de talco ou pirofilita, mas oferece materiais comparativos lamelares e magnesianos úteis para contraste estrutural e geoquímico, especialmente VTx-1 e PFl-1.",
        "samples": [
            {
                "code": "VTx-1",
                "label": "Vermiculite (Llano)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Material comparativo magnesiano hidratado; não equivale a talco ou pirofilita."},
                ],
            },
            {
                "code": "PFl-1",
                "label": "Palygorskite (Attapulgite)",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Material comparativo de argila magnesiana para contraste com filossilicatos não expansivos."},
                ],
            },
        ],
    },
    "pyrophyllite_talc_related": {
        "summary": "Para materiais relacionados ao eixo pirofilita-talco, o acervo Source Clays pode ser usado apenas de forma comparativa, com destaque para VTx-1 e PFl-1.",
        "samples": [
            {
                "code": "VTx-1",
                "label": "Vermiculite (Llano)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo magnesiano; não é padrão direto do mineral desta página."},
                ],
            },
            {
                "code": "PFl-1",
                "label": "Palygorskite (Attapulgite)",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo laboratorial para materiais lamelares e fibrosos ricos em Mg."},
                ],
            },
        ],
    },
    "short_range_order": {
        "summary": "A Clay Minerals Society não oferece um padrão direto para alofana ou imogolita, mas o repositório pode apoiar comparações com argilas muito reativas e materiais de baixa cristalinidade, especialmente KGa-2 e SWy-2.",
        "samples": [
            {
                "code": "KGa-2",
                "label": "Kaolin high-defect",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo de aluminossilicato desordenado; não substitui um padrão direto de baixa ordem estrutural."},
                ],
            },
            {
                "code": "SWy-2",
                "label": "Na-Montmorillonite Wyoming",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo de material expansivo e muito reativo em estudos de superfície e adsorção."},
                ],
            },
        ],
    },
    "layered_double_hydroxide": {
        "summary": "A Clay Minerals Society não mantém um padrão direto para hidróxidos duplos lamelares, mas alguns materiais especiais e magnesianos do acervo ajudam em comparações geoquímicas e de reatividade superficial.",
        "samples": [
            {
                "code": "VTx-1",
                "label": "Vermiculite (Llano)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo lamelar hidratado e magnesiano; não é um LDH."},
                ],
            },
            {
                "code": "CCa-2",
                "label": "Ripidolite (Chlorite)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo Fe-Mg de fase lamelar; não corresponde diretamente a hidrotalcitas."},
                ],
            },
        ],
    },
    "phyllosilicate_related": {
        "summary": "Para materiais relacionados ao universo mais amplo dos filossilicatos, o Source Clays Repository pode ser usado como base comparativa com padrões clássicos de caulinita, esmectita, ilita e clorita.",
        "samples": [
            {
                "code": "KGa-1b",
                "label": "Kaolin low-defect",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo para filossilicatos aluminossilicatados 1:1."},
                ],
            },
            {
                "code": "SWy-2",
                "label": "Na-Montmorillonite Wyoming",
                "facts": [
                    {"label": "Tipo", "value": "Source Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo para filossilicatos 2:1 expansivos."},
                ],
            },
            {
                "code": "CCa-2",
                "label": "Ripidolite (Chlorite)",
                "facts": [
                    {"label": "Tipo", "value": "Special Clay"},
                    {"label": "Uso curatorial", "value": "Comparativo para filossilicatos Fe-Mg de baixo grau metamórfico."},
                ],
            },
        ],
    },
    "mixed_layer": {
        "summary": "Para argilominerais interestratificados, a Clay Minerals Society disponibiliza o padrão ISMt-2 como material comparativo de ilita-esmectita.",
        "samples": [
            {"code": "ISMt-2", "label": "Illite-Smectite mixed layer", "facts": [{"label": "Tipo", "value": "Special Clay"}]},
        ],
    },
}

# Sinteses familiares usadas como fallback quando o Handbook nao foi curado
# diretamente para uma especie especifica.
HANDBOOK_FAMILY_REFERENCES = {
    "kaolin_group": {
        "summary": "A família caulinítica reúne filossilicatos 1:1 aluminossilicatados, muito frequentes em perfis de alteração intempérica, caulins e contextos hidrotermais de baixa temperatura.",
        "occurrence": "Minerais desta família tendem a formar-se por alteração de feldspatos e outros silicatos aluminosos em perfis de intemperismo, ambientes supergênicos e sistemas hidrotermais de baixa temperatura.",
        "association": "Quartzo, feldspatos, micas, alofana, gibbsita e outros aluminossilicatos de alteração.",
        "distribution": "São amplamente distribuídos em depósitos de caulim, solos altamente intemperizados e rochas alteradas em diferentes continentes.",
    },
    "smectite_group": {
        "summary": "As esmectitas são filossilicatos 2:1 expansivos, com água e cátions interlamelares variáveis, centrais para bentonitas, argilas de alteração e processos de adsorção e troca catiônica.",
        "occurrence": "O grupo ocorre por alteração de vidros vulcânicos, tufos e cinzas, em sedimentos de baixa temperatura, solos, sistemas hidrotermais rasos e ambientes supergênicos.",
        "association": "Zeólitas, feldspatos alterados, quartzo, calcita, opala, paligorsquita e outros filossilicatos 2:1.",
        "distribution": "Possui distribuição mundial em bentonitas, depósitos lacustres e marinhos, solos e sequências vulcano-sedimentares alteradas.",
    },
    "smectite_related": {
        "summary": "Materiais argilosos relacionados às esmectitas, como bentonitas e terra de fuller, são interpretados na Argiloteca como domínios sedimentares e tecnológicos ligados a minerais expansivos 2:1.",
        "occurrence": "Costumam ocorrer em níveis bentoníticos, argilas sedimentares alteradas e materiais finos derivados de cinzas vulcânicas ou retrabalhamento de esmectitas.",
        "association": "Montmorilonita, beidellita, nontronita, hectorita, quartzo fino, feldspatos alterados e carbonatos.",
        "distribution": "São amplamente conhecidos em bacias sedimentares, depósitos de bentonita e unidades argilosas com uso industrial.",
    },
    "illite_mica": {
        "summary": "A família ilita-mica reúne filossilicatos 2:1 não expansivos, comuns em sedimentos diagenéticos, argilas maduras, folhelhos e sucessões alteradas ricas em K.",
        "occurrence": "Esses minerais ocorrem em folhelhos, siltitos, solos, sistemas diagenéticos e em alterações hidrotermais ou de baixo grau metamórfico de materiais ricos em K.",
        "association": "Quartzo, feldspatos, caulinita, esmectitas, cloritas, carbonatos e óxidos de ferro.",
        "distribution": "São muito difundidos em rochas sedimentares finas, perfis de intemperismo e sequências metassedimentares de baixo grau.",
    },
    "mica_group": {
        "summary": "As micas e micas argilosas do vocabulário representam filossilicatos 2:1 não expansivos, com forte importância em petrologia, diagênese e alteração de rochas alumino-potássicas.",
        "occurrence": "Costumam ocorrer em ambientes magmáticos, metamórficos e diagenéticos, além de perfis de alteração de feldspatos e minerais ferromagnesianos.",
        "association": "Quartzo, feldspatos, cloritas, talco, esmectitas, granadas e anfibólios, conforme o contexto geológico.",
        "distribution": "Têm distribuição mundial em rochas cristalinas, sedimentos finos e sequências metamórficas.",
    },
    "chlorite_group": {
        "summary": "As cloritas constituem filossilicatos 2:1:1 típicos de alteração de minerais ferromagnesianos e de metamorfismo de baixo grau, com ampla variedade composicional.",
        "occurrence": "São comuns em rochas máficas e ultramáficas alteradas, xistos verdes, veios hidrotermais e produtos de alteração de biotita, anfibólios e piroxênios.",
        "association": "Epidoto, albita, actinolita, quartzo, calcita, biotita, talco, serpentina e minerais opacos.",
        "distribution": "O grupo é globalmente distribuído em rochas metamórficas, hidrotermais e ultramáficas alteradas.",
    },
    "chlorite_related": {
        "summary": "Materiais relacionados às cloritas preservam o contexto de alteração ferromagnesiana e baixo grau metamórfico típico do ramo clorítico.",
        "occurrence": "Aparecem em rochas alteradas ricas em Fe-Mg, associações hidrotermais e interestratificações com outros filossilicatos.",
        "association": "Cloritas, vermiculitas, esmectitas ferríferas, talco e serpentina.",
        "distribution": "Têm ocorrência espalhada em ambientes metamórficos, hidrotermais e supergênicos ligados a rochas máficas.",
    },
    "vermiculite_group": {
        "summary": "A vermiculita ocupa um domínio entre micas e argilas expansivas, marcada por forte hidratação interlamelar e expansão térmica característica.",
        "occurrence": "Forma-se sobretudo por alteração de biotita e flogopita em contextos intempéricos, hidrotermais e metamórficos de baixo grau.",
        "association": "Biotita, flogopita, clorita, talco, serpentina, apatita e carbonatos.",
        "distribution": "É conhecida em depósitos de alteração máfica e ultramáfica, além de solos e materiais micáceos alterados em diferentes continentes.",
    },
    "vermiculite_related": {
        "summary": "Materiais relacionados à vermiculita preservam o contexto de hidratação interlamelar e transformação progressiva de micas Fe-Mg.",
        "occurrence": "Aparecem em perfis de alteração e zonas de transição entre micas, cloritas e filossilicatos expansivos.",
        "association": "Biotita, clorita, talco, esmectitas e serpentinas.",
        "distribution": "Distribuem-se em depósitos de alteração micácea e ambientes supergênicos.",
    },
    "palygorskite_sepiolite_group": {
        "summary": "Este ramo reúne argilominerais fibrosos ricos em Mg, importantes em ambientes áridos, lacustres e evaporíticos, além de usos adsorventes e tecnológicos.",
        "occurrence": "São típicos de bacias alcalinas e salinas, sedimentos magnésicos, paleossolos, carbonatos e ambientes evaporíticos ou de alteração de silicatos magnesianos.",
        "association": "Dolomita, calcita, opala, quartzo, esmectitas, talco e minerais evaporíticos.",
        "distribution": "Têm ocorrência relevante em bacias continentais áridas, depósitos sedimentares magnesianos e materiais industriais especializados.",
    },
    "serpentine_group": {
        "summary": "O grupo da serpentina reúne filossilicatos 1:1 magnésicos formados principalmente por serpentinização de rochas ultramáficas e contextos metamórficos associados.",
        "occurrence": "Esses minerais são típicos da alteração hidrotermal e metamórfica de peridotitos, dunitos e outras rochas ultramáficas, formando serpentinitos.",
        "association": "Brucita, magnetita, talco, clorita, cromita, carbonatos e anfibólios, conforme o estágio da serpentinização.",
        "distribution": "São amplamente distribuídos em cinturões ofiolíticos, complexos ultramáficos, zonas de falha e maciços metamórficos.",
    },
    "pyrophyllite_talc": {
        "summary": "A família pirofilita-talco reúne filossilicatos 2:1 não expansivos dominados por Al ou Mg, importantes em metamorfismo, hidrotermalismo e materiais industriais.",
        "occurrence": "Aparecem em veios hidrotermais, rochas metamórficas aluminosa ou magnesianas, esteatitos e corpos alterados de baixo grau a médio grau.",
        "association": "Quartzo, cianita, andaluzita, topázio, dolomita, clorita, anfibólios e carbonatos.",
        "distribution": "Têm distribuição ampla em províncias metamórficas e depósitos hidrotermais de vários continentes.",
    },
    "pyrophyllite_talc_related": {
        "summary": "Os materiais relacionados à família pirofilita-talco preservam o contexto de filossilicatos 2:1 não expansivos em ambientes metamórficos e hidrotermais.",
        "occurrence": "São encontrados em rochas alteradas aluminosas ou magnesianas e em depósitos metamórfico-hidrotermais especializados.",
        "association": "Pirofilita, talco, quartzo, clorita, carbonatos e anfibólios.",
        "distribution": "Ocorrem em domínios metamórficos e corpos hidrotermais em diferentes regiões.",
    },
    "phyllosilicate_related": {
        "summary": "Este conjunto reúne materiais ligados ao universo dos filossilicatos por textura, composição ou contexto de ocorrência.",
        "occurrence": "Aparecem em sistemas de alteração, perfis superficiais e rochas finas ricas em silicatos hidratados.",
        "association": "Quartzo, feldspatos, micas, cloritas, esmectitas e óxidos de ferro.",
        "distribution": "Apresentam distribuição variada em ambientes sedimentares, intempéricos e hidrotermais.",
    },
    "short_range_order": {
        "summary": "Os minerais de baixa ordem estrutural do vocabulário representam materiais aluminosilicáticos mal cristalizados, fortemente ligados a solos vulcânicos e intemperismo avançado.",
        "occurrence": "Costumam ocorrer em cinzas vulcânicas alteradas, horizontes andossólicos, saprolitos e ambientes de intensa hidratação e reorganização de aluminossilicatos.",
        "association": "Alofana, imogolita, quartzo, cristobalita, gibbsita, vermiculita e óxidos hidratados de ferro.",
        "distribution": "São particularmente importantes em solos derivados de material vulcânico, mas podem ocorrer em outros ambientes supergênicos ricos em Al e Si.",
    },
    "layered_double_hydroxide": {
        "summary": "Os hidróxidos duplos lamelares do vocabulário reúnem fases hidratadas ricas em Mg, Al, Fe e ânions interlamelares, relevantes em geoquímica de alteração alcalina e ambientes salinos.",
        "occurrence": "Costumam formar-se em sistemas altamente alcalinos, zonas de alteração supergênica, serpentinitos alterados e ambientes evaporíticos ou ricos em salmouras.",
        "association": "Brucita, carbonatos, serpentinas, óxidos de Fe-Mn e sais evaporíticos.",
        "distribution": "Possuem ocorrência mais especializada, porém amplamente reconhecida em sistemas hiperalcalinos e em depósitos ligados a ultramáficas alteradas.",
    },
    "mixed_layer": {
        "summary": "Os argilominerais interestratificados registram transições estruturais entre famílias de filossilicatos, importantes para diagnóstico diagenético, intempérico e hidrotermal.",
        "occurrence": "Surgem em trajetórias de transformação entre esmectitas, ilitas, cloritas e vermiculitas, tanto em diagênese quanto em alteração supergênica e hidrotermal.",
        "association": "Illite, smectite, chlorite, vermiculite, quartzo, feldspatos alterados e carbonatos.",
        "distribution": "São frequentes em folhelhos, bentonitas alteradas, perfis de intemperismo e materiais finos com história mineralógica mista.",
    },
}

# EarthChem e uma rota de descoberta de datasets, nao uma fonte primaria de
# padrao DRX; por isso os blocos abaixo orientam escopo e estrategia de busca.
EARTHCHEM_FAMILY_REFERENCES = {
    "kaolin_group": {
        "summary": "O EarthChem pode complementar a leitura destes minerais com datasets geoquímicos e amostrais associados a solos, perfis de alteração, argilas aluminossilicatadas e materiais sedimentares finos.",
        "data_scope": "Dados geoquímicos integrados, amostras e referências associadas a materiais argilosos e produtos de alteração aluminossilicática.",
    },
    "smectite_group": {
        "summary": "O EarthChem pode apoiar a navegação por datasets geoquímicos, amostras e referências ligados a esmectitas, bentonitas e materiais finos de alteração vulcânica ou sedimentar.",
        "data_scope": "Dados de química total, traços, petrologia e metadados amostrais em sistemas geológicos onde filossilicatos 2:1 expansivos aparecem como alteração ou produto sedimentar.",
    },
    "smectite_related": {
        "summary": "O EarthChem oferece contexto geoquímico útil para materiais relacionados a esmectitas, especialmente em depósitos bentoníticos e argilas industriais.",
        "data_scope": "Dados amostrais e geoquímicos de materiais argilosos finos, com ênfase em contextos sedimentares e vulcano-sedimentares.",
    },
    "illite_mica": {
        "summary": "O EarthChem pode complementar estas páginas com datasets ligados a rochas finas, diagênese, alteração potássica e contextos sedimentares ou metamórficos de baixo grau.",
        "data_scope": "Tabelas integradas de química e metadados de amostras em rochas sedimentares, pelíticas e alteradas ricas em filossilicatos 2:1 não expansivos.",
    },
    "mica_group": {
        "summary": "O EarthChem pode servir como ponte entre o perfil mineralógico local e datasets geoquímicos de micas, rochas alumino-potássicas e materiais metamórficos.",
        "data_scope": "Dados geoquímicos, petrológicos e de proveniência de materiais ricos em micas e silicatos lamelares associados.",
    },
    "chlorite_group": {
        "summary": "O EarthChem ajuda a localizar amostras e datasets geoquímicos de rochas máficas, ultramáficas e metamórficas onde cloritas são minerais importantes de alteração e baixo grau.",
        "data_scope": "Dados geoquímicos integrados de rochas alteradas Fe-Mg, sequências metamórficas e contextos hidrotermais com cloritas.",
    },
    "chlorite_related": {
        "summary": "O EarthChem é útil para rastrear contextos geoquímicos de materiais ferrimagnesianos alterados relacionados a cloritas.",
        "data_scope": "Dados de química e metadados amostrais em contextos hidrotermais, metamórficos e supergênicos de rochas máficas.",
    },
    "vermiculite_group": {
        "summary": "O EarthChem pode complementar a interpretação geoquímica de materiais hidratados derivados de micas Fe-Mg e seus ambientes de alteração.",
        "data_scope": "Dados geoquímicos de solos, rochas alteradas e materiais micáceos hidratados.",
    },
    "vermiculite_related": {
        "summary": "O EarthChem pode ajudar a localizar amostras e análises relacionadas à transformação de micas em materiais expansíveis hidratados.",
        "data_scope": "Química total, traços e metadados de materiais micáceos alterados e solos.",
    },
    "palygorskite_sepiolite_group": {
        "summary": "O EarthChem pode ampliar o contexto geoquímico de argilominerais fibrosos associados a ambientes áridos, evaporíticos e magnésicos.",
        "data_scope": "Dados geoquímicos e amostrais de sedimentos alcalinos, bacias evaporíticas, carbonatos magnésicos e materiais adsorventes naturais.",
    },
    "serpentine_group": {
        "summary": "O EarthChem é especialmente valioso aqui para conectar os perfis locais a amostras e datasets de rochas ultramáficas, serpentinitos e sistemas de alteração hidrotermal.",
        "data_scope": "Geoquímica de peridotitos, dunitos, serpentinitos e contextos de serpentinização, com amostras e referências integradas em múltiplos sistemas.",
    },
    "pyrophyllite_talc": {
        "summary": "O EarthChem pode fornecer continuidade entre estes minerais e amostras de rochas metamórficas, esteatitos, alterações hidrotermais e silicatos Al-Mg relacionados.",
        "data_scope": "Dados de química total, traços e metadados petrológicos em veios, xistos, esteatitos e rochas alteradas ricas em filossilicatos 2:1 não expansivos.",
    },
    "pyrophyllite_talc_related": {
        "summary": "O EarthChem ajuda a contextualizar materiais do universo pirofilita-talco em rochas metamórficas e alteradas.",
        "data_scope": "Geoquímica e metadados de amostras aluminosa ou magnesianas em contextos metamórficos e hidrotermais.",
    },
    "short_range_order": {
        "summary": "O EarthChem pode ser usado para localizar amostras e datasets de solos vulcânicos, saprolitos e materiais mal cristalizados relevantes para alofana, imogolita e análogos.",
        "data_scope": "Dados geoquímicos, amostrais e de materiais de alteração em solos vulcânicos e ambientes de baixa ordem estrutural.",
    },
    "layered_double_hydroxide": {
        "summary": "O EarthChem pode complementar estes perfis com amostras e dados geoquímicos de sistemas alcalinos, evaporíticos e ultramáficos alterados onde LDHs são relevantes.",
        "data_scope": "Geoquímica de ambientes hiperalcalinos, salmouras, carbonatos e ultramáficas alteradas com fases hidratadas lamelares.",
    },
    "mixed_layer": {
        "summary": "O EarthChem pode ampliar a interpretação dos argilominerais interestratificados com datasets ligados a transições diagenéticas e de alteração entre famílias de filossilicatos.",
        "data_scope": "Dados geoquímicos e amostrais em folhelhos, bentonitas alteradas e materiais finos com história mineralógica mista.",
    },
    "phyllosilicate_related": {
        "summary": "O EarthChem pode oferecer contexto amplo para materiais ligados ao universo dos filossilicatos em rochas finas, solos e sistemas de alteração.",
        "data_scope": "Dados geoquímicos integrados de materiais finos silicáticos e ambientes sedimentares ou intempéricos.",
    },
}

# Classes estruturais locais mantem a navegacao consistente quando as fontes
# externas usam terminologia diferente ou incompleta.
STRUCTURAL_CLASS_BY_TERM = {
    "kaolin": "Filossilicato 1:1",
    "kaolinite": "Filossilicato 1:1",
    "dickite": "Filossilicato 1:1",
    "nacrite": "Filossilicato 1:1",
    "halloysite": "Filossilicato 1:1",
    "endellite": "Filossilicato 1:1",
    "smectite": "Filossilicato 2:1 expansivo",
    "montmorillonite": "Filossilicato 2:1 expansivo",
    "beidellite": "Filossilicato 2:1 expansivo",
    "nontronite": "Filossilicato 2:1 expansivo ferrifero",
    "saponite": "Filossilicato 2:1 expansivo",
    "hectorite": "Filossilicato 2:1 expansivo",
    "stevensite": "Filossilicato 2:1 expansivo",
    "sauconite": "Filossilicato 2:1 expansivo",
    "swinefordite": "Filossilicato 2:1 expansivo",
    "volkonskoite": "Filossilicato 2:1 expansivo",
    "yakhontovite": "Filossilicato 2:1 expansivo",
    "illite": "Filossilicato 2:1 nao expansivo",
    "glauconite": "Filossilicato 2:1 nao expansivo",
    "celadonite": "Filossilicato 2:1 nao expansivo",
    "muscovite": "Filossilicato 2:1 nao expansivo",
    "paragonite": "Filossilicato 2:1 nao expansivo",
    "phlogopite": "Filossilicato 2:1 nao expansivo",
    "biotite": "Filossilicato 2:1 nao expansivo",
    "lepidolite": "Filossilicato 2:1 nao expansivo",
    "margarite": "Filossilicato 2:1 nao expansivo",
    "clintonite": "Filossilicato 2:1 nao expansivo",
    "brammallite": "Filossilicato 2:1 nao expansivo",
    "sericite": "Filossilicato 2:1 nao expansivo",
    "chlorite": "Filossilicato 2:1:1",
    "clinochlore": "Filossilicato 2:1:1",
    "chamosite": "Filossilicato 2:1:1",
    "nimite": "Filossilicato 2:1:1",
    "pennantite": "Filossilicato 2:1:1",
    "cookeite": "Filossilicato 2:1:1",
    "sudoite": "Filossilicato 2:1:1",
    "donbassite": "Filossilicato 2:1:1",
    "baileychlore": "Filossilicato 2:1:1",
    "vermiculite": "Filossilicato 2:1",
    "palygorskite": "Argilomineral fibroso",
    "sepiolite": "Argilomineral fibroso",
    "serpentine": "Filossilicato 1:1",
    "lizardite": "Filossilicato 1:1",
    "chrysotile": "Filossilicato 1:1 fibroso",
    "antigorite": "Filossilicato 1:1",
    "pyrophyllite": "Filossilicato 2:1 nao expansivo",
    "talc": "Filossilicato 2:1 nao expansivo",
    "kerolite": "Filossilicato 2:1 trioctaedrico",
}

STRUCTURAL_CLASS_BY_FAMILY = {
    "kaolin_group": "Filossilicato 1:1",
    "serpentine_group": "Filossilicato 1:1",
    "smectite_group": "Filossilicato 2:1 expansivo",
    "smectite_related": "Filossilicato 2:1 expansivo",
    "illite_mica": "Filossilicato 2:1 nao expansivo",
    "mica_group": "Filossilicato 2:1 nao expansivo",
    "chlorite_group": "Filossilicato 2:1:1",
    "chlorite_related": "Filossilicato 2:1:1",
    "vermiculite_group": "Filossilicato 2:1",
    "vermiculite_related": "Filossilicato 2:1",
    "palygorskite_sepiolite_group": "Argilomineral fibroso",
    "pyrophyllite_talc": "Filossilicato 2:1 nao expansivo",
    "short_range_order": "Argilomineral de baixa ordem estrutural",
    "layered_double_hydroxide": "Hidroxido duplo lamelar",
    "mixed_layer": "Argilomineral interestratificado",
}

GROUP_LABEL_BY_FAMILY = {
    "mica_group": "Grupo ilita e micas relacionadas",
    "chlorite_related": "Grupo das cloritas",
    "vermiculite_related": "Grupo da vermiculita",
    "smectite_related": "Grupo das esmectitas",
}

COMMUNITY_SLUG_BY_GROUP_KEY = {
    "kaolin_group": "caulim-serpentina",
    "grupo da caulinita": "caulim-serpentina",
    "grupo da caulinita-serpentina": "caulim-serpentina",
    "grupo do caulim-serpentina": "caulim-serpentina",
    "caulim-serpentina": "caulim-serpentina",
    "serpentine_group": "caulim-serpentina",
    "grupo da serpentina": "caulim-serpentina",
    "smectite_group": "esmectitas",
    "grupo das esmectitas": "esmectitas",
    "esmectitas": "esmectitas",
    "illite_mica": "micas-argilosas-ilitas",
    "mica_group": "micas-argilosas-ilitas",
    "grupo ilita e micas relacionadas": "micas-argilosas-ilitas",
    "grupo das micas argilosas e ilitas": "micas-argilosas-ilitas",
    "micas argilosas e ilitas": "micas-argilosas-ilitas",
    "chlorite_group": "cloritas",
    "chlorite_related": "cloritas",
    "grupo das cloritas": "cloritas",
    "cloritas": "cloritas",
    "vermiculite_group": "vermiculitas",
    "vermiculite_related": "vermiculitas",
    "grupo da vermiculita": "vermiculitas",
    "grupo das vermiculitas": "vermiculitas",
    "vermiculitas": "vermiculitas",
    "smectite_related": "esmectitas",
    "palygorskite_sepiolite_group": "sepiolita-paligorsquita",
    "grupo paligorsquita-sepiolita": "sepiolita-paligorsquita",
    "sepiolita e paligorsquita": "sepiolita-paligorsquita",
    "sepiolita-paligorsquita": "sepiolita-paligorsquita",
    "pyrophyllite_talc": "pirofilita-talco",
    "grupo pirofilita-talco": "pirofilita-talco",
    "pirofilita-talco": "pirofilita-talco",
    "short_range_order": "alofana-imogolita",
    "minerais de baixa ordem estrutural": "alofana-imogolita",
    "alofana e imogolita": "alofana-imogolita",
    "alofana-imogolita": "alofana-imogolita",
    "layered_double_hydroxide": "hidrotalcitas-hidroxidos-duplos-lamelares",
    "hidroxidos duplos lamelares": "hidrotalcitas-hidroxidos-duplos-lamelares",
    "hidróxidos duplos lamelares": "hidrotalcitas-hidroxidos-duplos-lamelares",
    "hidrotalcitas e hidroxidos duplos lamelares": "hidrotalcitas-hidroxidos-duplos-lamelares",
    "hidrotalcitas e hidróxidos duplos lamelares": "hidrotalcitas-hidroxidos-duplos-lamelares",
    "hidrotalcitas-hidroxidos-duplos-lamelares": "hidrotalcitas-hidroxidos-duplos-lamelares",
    "mixed_layer": "argilominerais-interestratificados",
    "argilominerais interestratificados": "argilominerais-interestratificados",
    "grupo dos argilominerais interestratificados": "argilominerais-interestratificados",
    "interestratificados": "argilominerais-interestratificados",
}


def clean_text(value):
    """Normalize strings and lightweight scalar values."""
    if value in (None, "", [], {}):
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, list):
        cleaned = [clean_text(item) for item in value]
        cleaned = [item for item in cleaned if item]
        return ", ".join(cleaned) if cleaned else None

    text = str(value).strip()
    return text or None


def clean_list(values):
    """Return unique cleaned labels while preserving first-seen order."""
    items = []
    seen = set()
    for value in values or []:
        text = clean_text(value)
        key = normalize_lookup_key(text)
        if not text or not key or key in seen:
            continue
        items.append(text)
        seen.add(key)
    return items


def clean_inline_text(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def split_mindat_reference_list(value):
    """Split a compact Mindat reference block into readable citation snippets."""
    text = clean_inline_text(value)
    if not text:
        return []

    text = re.sub(r"^\w+\s+Reference List:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^Reference List:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^Year\s+⬇\s+Author\s+Title\s+Publisher\s*", "", text, flags=re.IGNORECASE)

    entry_start = r"[A-ZÀ-ÖØ-Ý][^()]{1,180}\(\d{4}\)"
    text = re.sub(
        rf"\.\s+(?={entry_start})",
        ". || ",
        text,
    )
    text = re.sub(
        rf"(doi:[^\s]+)\s+(?={entry_start})",
        r"\1 || ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"(\d{{1,4}}(?:-\d{{1,4}})?)\s+(?={entry_start})",
        r"\1 || ",
        text,
    )

    items = []
    parts = text.split("||")
    for item in parts:
        item = clean_inline_text(item)
        if not item:
            continue
        if len(item) < 20:
            continue
        items.append(item)

    merged = []
    for item in items:
        if (
            merged
            and re.match(r"^\(\d{4}\)", item)
            and not re.search(r"\(\d{4}\)", merged[-1])
        ):
            merged[-1] = clean_inline_text(f"{merged[-1]} {item}")
            continue
        if (
            merged
            and not re.search(r"\(\d{4}\)", item)
            and re.search(r"\(\d{4}\)", merged[-1])
        ):
            merged[-1] = clean_inline_text(f"{merged[-1]} {item}")
            continue
        merged.append(item)
    return merged


CURATORIAL_FACT_LABELS = {
    "nome_cientifico_padronizado": "Nome científico padronizado",
    "nome_pt": "Nome em português",
    "nome_en": "Nome em inglês",
    "formula_ideal": "Fórmula ideal",
    "grupo_mineralogico": "Grupo mineralógico",
    "classe_estrutural": "Classe estrutural",
    "sistema_cristalino": "Sistema cristalino",
    "classificacao_ima_mindat": "IMA Classification",
    "ambiente_tipico_formacao": "Ambiente típico de formação",
    "aliases": "Aliases",
    "subjects": "Assuntos Invenio",
    "descricao_curta": "Síntese curta",
    "licenca_fonte": "Licença da fonte",
    "observacao_proveniencia": "Proveniência",
    "external_uri": "URI externa",
    "community_slug": "Comunidade temática na Argiloteca",
}

CURATORIAL_FACT_ORDER = [
    "nome_cientifico_padronizado",
    "nome_pt",
    "nome_en",
    "classificacao_ima_mindat",
    "ambiente_tipico_formacao",
    "aliases",
    "subjects",
    "descricao_curta",
    "external_uri",
]

CURATORIAL_FACT_EXCLUDED_KEYS = {
    "classic_description",
    "reference",
    "quimica_mindat",
    "difracao_raios_x_po_mindat",
    "petrologia_mindat",
    "referencias_mindat",
    "mindat_sections",
    "descricao_classica",
}


def normalize_lookup_key(value):
    """Normalize keys for tolerant comparisons and lightweight matching."""
    text = clean_text(value)
    if not text:
        return None

    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None


def _stringify_curatorial_value(value):
    """Convert scalar/list metadata into a fact value suitable for display."""
    if value in (None, "", [], {}):
        return None

    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            items = []
            for item in value:
                text = clean_text(
                    item.get("subject")
                    or item.get("title")
                    or item.get("label")
                    or item.get("name")
                )
                if text:
                    items.append(text)
            return clean_text(items)
        return clean_text(value)

    if isinstance(value, dict):
        return None

    return clean_text(value)


def build_curatorial_facts(mineral):
    """Build ordered, deduplicated facts shown in the mineral profile."""
    mineral = mineral or {}
    facts = []
    seen_values = set()

    for key in CURATORIAL_FACT_ORDER:
        value = _stringify_curatorial_value(mineral.get(key))
        if not value:
            continue
        marker = (CURATORIAL_FACT_LABELS.get(key, key), normalize_lookup_key(value))
        if marker in seen_values:
            continue
        facts.append(
            {
                "key": key,
                "label": CURATORIAL_FACT_LABELS.get(key, key.replace("_", " ").title()),
                "value": value,
                "href": (
                    value
                    if key == "external_uri"
                    else f"/communities/{value}"
                    if key == "community_slug"
                    else None
                ),
            }
        )
        seen_values.add(marker)

    return facts


def build_license_entries(mineral):
    """Collect source/license statements for the profile transparency panel."""
    mineral = mineral or {}
    entries = []
    seen = set()

    reference = mineral.get("reference") or resolve_external_reference(mineral)
    reference_source = clean_text(reference.get("source"))
    reference_license = clean_text(mineral.get("licenca_fonte"))
    reference_uri = clean_text(reference.get("uri"))
    reference_note = clean_text(mineral.get("observacao_proveniencia"))

    if reference_source and reference_license:
        marker = (normalize_lookup_key(reference_source), normalize_lookup_key(reference_license))
        if marker not in seen:
            entries.append(
                {
                    "source": reference_source,
                    "license": reference_license,
                    "href": reference_uri,
                    "note": reference_note,
                }
            )
            seen.add(marker)

    for block in mineral.get("scientific_source_blocks") or []:
        source = clean_text(block.get("title"))
        license_text = clean_text(block.get("license"))
        href = clean_text(block.get("href"))
        note = clean_text(block.get("provenance"))
        if not source or not license_text:
            continue
        marker = (normalize_lookup_key(source), normalize_lookup_key(license_text))
        if marker in seen:
            continue
        entries.append(
            {
                "source": source,
                "license": license_text,
                "href": href,
                "note": note,
            }
        )
        seen.add(marker)

    return entries


def build_reusable_image_profile(identifier, mineral):
    """Resolve exact or family-level image metadata for one mineral profile."""
    family_id = clean_text(mineral.get("familia_vocabulario"))
    family_reference = deepcopy(REUSABLE_IMAGE_FAMILY_REFERENCES.get(family_id) or {})
    identifier = clean_text(identifier)
    curated = deepcopy(load_curated_reusable_images().get(identifier) or {})
    exact_reference = None
    if curated and any(pattern in (clean_text(curated.get("image_url")) or "") for pattern in NON_EMBEDDABLE_IMAGE_PATTERNS):
        exact_reference = {
            "exact_page_url": clean_text(curated.get("page_url")),
            "exact_title": clean_text(curated.get("title")),
            "exact_source": clean_text(curated.get("source_name")),
            "exact_license": clean_text(curated.get("license")),
            "exact_credit": clean_text(curated.get("credit")),
            "exact_locality": clean_text(curated.get("locality")),
            "exact_note": (
                "Existe uma imagem exata curada para este termo, mas a fonte original nao permite incorporacao direta na interface. "
                "Use o link abaixo para abrir a pagina original da imagem."
            ),
        }
        curated = {}
    if curated and not any(pattern in (clean_text(curated.get("image_url")) or "") for pattern in NON_EMBEDDABLE_IMAGE_PATTERNS):
        curated["scope_label"] = clean_text(curated.get("scope_label")) or "Imagem exata do termo"
        curated["scope_note"] = clean_text(curated.get("scope_note")) or "A imagem exibida foi curada especificamente para este argilomineral."
    else:
        curated = family_reference
        if not curated:
            return None

    return {
        "source": clean_text(curated.get("source_name")),
        "title": clean_text(curated.get("title")),
        "image_url": clean_text(curated.get("image_url")),
        "page_url": clean_text(curated.get("page_url")),
        "license": clean_text(curated.get("license")),
        "credit": clean_text(curated.get("credit")),
        "locality": clean_text(curated.get("locality")),
        "provenance": clean_text(curated.get("provenance")),
        "scope_label": clean_text(curated.get("scope_label")),
        "scope_note": clean_text(curated.get("scope_note")),
        "exact_page_url": clean_text((exact_reference or {}).get("exact_page_url")),
        "exact_title": clean_text((exact_reference or {}).get("exact_title")),
        "exact_source": clean_text((exact_reference or {}).get("exact_source")),
        "exact_license": clean_text((exact_reference or {}).get("exact_license")),
        "exact_credit": clean_text((exact_reference or {}).get("exact_credit")),
        "exact_locality": clean_text((exact_reference or {}).get("exact_locality")),
        "exact_note": clean_text((exact_reference or {}).get("exact_note")),
    }


def _load_json_file(path):
    """Load an optional curated JSON file, returning an empty mapping if absent."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_curated_mindat_seeds():
    """Load curated Mindat seed fields keyed by local mineral id."""
    return _load_json_file(CURATED_SEEDS_PATH)


@lru_cache(maxsize=1)
def load_curated_handbook_profiles():
    """Load direct Handbook-derived profiles keyed by local mineral id."""
    return _load_json_file(HANDBOOK_CURATED_PATH)


@lru_cache(maxsize=1)
def load_curated_source_clays_profiles():
    """Load direct Source Clays profiles keyed by local mineral id."""
    return _load_json_file(SOURCE_CLAYS_CURATED_PATH)


@lru_cache(maxsize=1)
def load_curated_reusable_images():
    """Load curated exact images keyed by local mineral id."""
    return _load_json_file(REUSABLE_IMAGE_CURATED_PATH)


@lru_cache(maxsize=1)
def load_argilominerais_vocabulary():
    """Load the authorized argilomineral vocabulary JSONL."""
    items = {}
    if not VOCABULARY_PATH.exists():
        return items

    for raw_line in VOCABULARY_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        item = json.loads(line)
        item_id = clean_text(item.get("id"))
        if item_id:
            items[item_id] = item
    return items


@lru_cache(maxsize=1)
def load_grupo_mineralogico_vocabulary():
    """Load the authorized mineral-group vocabulary JSONL."""
    items = {}
    if not GROUP_VOCABULARY_PATH.exists():
        return items

    for raw_line in GROUP_VOCABULARY_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        item = json.loads(line)
        item_id = clean_text(item.get("id"))
        if item_id:
            items[item_id] = item
    return items


@lru_cache(maxsize=1)
def _mineral_lookup_index():
    """Index ids, labels and broader terms to canonical mineral ids."""
    seeds = load_curated_mindat_seeds()
    vocabulary = load_argilominerais_vocabulary()
    index = {}
    broader_candidates = []

    for identifier in sorted(set(seeds) | set(vocabulary)):
        seed = seeds.get(identifier) or {}
        vocab = vocabulary.get(identifier) or {}
        titles = vocab.get("title") or {}
        props = vocab.get("props") or {}

        primary_aliases = [
            identifier,
            titles.get("pt"),
            titles.get("en"),
            seed.get("nome"),
            seed.get("nome_pt"),
            seed.get("nome_cientifico_padronizado"),
        ]

        broader = clean_text(props.get("broader"))
        for alias in clean_list(primary_aliases):
            alias_key = normalize_lookup_key(alias)
            if alias_key and alias_key not in index:
                index[alias_key] = identifier

        if broader:
            broader_candidates.append((normalize_lookup_key(broader), identifier))

    for broader_key, identifier in broader_candidates:
        if broader_key and broader_key not in index:
            index[broader_key] = identifier

    return index


def lowercase_first(text):
    """Lowercase only the first character to keep formulas intact."""
    normalized = clean_text(text)
    if not normalized:
        return None
    return normalized[:1].lower() + normalized[1:]


def localize_crystal_system(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    crystal = clean_text(value)
    if not crystal:
        return None
    translations = {
        "triclinic": "Triclinico",
        "monoclinic": "Monoclinico",
        "orthorhombic": "Ortorrômbico",
        "trigonal": "Trigonal",
        "hexagonal": "Hexagonal",
        "tetragonal": "Tetragonal",
        "cubic": "Cubico",
        "isometric": "Cubico",
    }
    return translations.get(crystal.casefold(), crystal)


def looks_like_english_group(value):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        value: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    group = clean_text(value)
    if not group:
        return False
    lowered = group.casefold()
    return any(token in lowered for token in (" group", " subgroup", " supergroup"))


def resolve_local_group_label(group_value=None, family_id=None):
    """Prefer Portuguese group labels from the local vocabulary when available."""
    group = clean_text(group_value)
    if group and not looks_like_english_group(group):
        return group

    family = clean_text(family_id)
    if family:
        group_vocab = load_grupo_mineralogico_vocabulary().get(family) or {}
        localized = clean_text((group_vocab.get("title") or {}).get("pt"))
        if localized:
            return localized
        override = clean_text(GROUP_LABEL_BY_FAMILY.get(family))
        if override:
            return override

    return group


def resolve_community_slug(*candidates):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *candidates: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for candidate in candidates:
        slug = resolve_group_community_slug(candidate)
        if slug:
            return slug
    return None


def resolve_structural_class(identifier, mineral=None):
    """Resolve the best structural class from curated fields or local maps."""
    mineral = mineral or {}
    return clean_text(
        mineral.get("classe_estrutural")
        or mineral.get("estrutura_cristalina")
        or STRUCTURAL_CLASS_BY_TERM.get(identifier)
        or STRUCTURAL_CLASS_BY_FAMILY.get(clean_text(mineral.get("familia_vocabulario")))
    )


def resolve_provenance_note(mineral):
    """Build a short provenance note for externally sourced mineral fields."""
    note = clean_text((mineral or {}).get("observacao_proveniencia"))
    if note:
        return note

    reference = resolve_external_reference(mineral)
    if reference["source"] == MINDAT_SOURCE and reference["uri"]:
        return (
            "Extracao estruturada a partir da pagina oficial do Mindat, com "
            "normalizacao local da Argiloteca para exibicao curatorial e navegacao."
        )
    return None


def resolve_mineral_name(mineral):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        mineral: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return clean_text(
        (mineral or {}).get("nome")
        or (mineral or {}).get("nome_cientifico_padronizado")
    )


def resolve_mineral_group(mineral):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        mineral: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    return clean_text(
        (mineral or {}).get("grupo_mineralogico") or (mineral or {}).get("grupo")
    )


def build_mindat_uri(external_id):
    """Build the canonical Mindat mineral URL from its numeric id."""
    identifier = clean_text(external_id)
    if not identifier:
        return None
    return f"https://www.mindat.org/min-{identifier}.html"


def parse_mindat_id(uri):
    """Extract a Mindat numeric id from a mineral page URL."""
    value = clean_text(uri)
    if not value:
        return None
    match = MINDAT_URI_PATTERN.match(value)
    return match.group("id") if match else None


def resolve_external_source(mineral):
    """Infer the external source name from explicit fields or URI/id shape."""
    mineral = mineral or {}
    source = clean_text(mineral.get("external_source"))
    uri = clean_text(mineral.get("external_uri"))
    identifier = clean_text(mineral.get("external_id"))

    if source:
        if source.lower() == "mindat":
            return MINDAT_SOURCE
        return source

    if parse_mindat_id(uri) or identifier:
        return MINDAT_SOURCE

    return None


def _first_nonempty(*values):
    """
    Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
    
    Args:
        *values: Valor de entrada consumido por esta etapa do fluxo.
    Returns:
        Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
    Raises:
        Exception: Propaga erros das dependências quando a validação ou o processamento falha.
    """
    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return None


def resolve_external_reference(mineral):
    """Return normalized source metadata without mutating the input."""
    mineral = mineral or {}
    source = resolve_external_source(mineral)
    identifier = clean_text(mineral.get("external_id")) or parse_mindat_id(
        mineral.get("external_uri")
    )
    uri = clean_text(mineral.get("external_uri"))

    if source == MINDAT_SOURCE and not uri and identifier:
        uri = build_mindat_uri(identifier)

    return {
        "source": source,
        "id": identifier,
        "uri": uri,
    }


def build_source_profiles(identifier):
    """Load direct source profiles curated for one local mineral id."""
    profiles = {}
    handbook = deepcopy(load_curated_handbook_profiles().get(identifier) or {})
    if handbook:
        profiles["handbook_mineralogy"] = handbook

    source_clays = deepcopy(load_curated_source_clays_profiles().get(identifier) or {})
    if source_clays:
        source_clays.setdefault("coverage_type", "direct")
        source_clays.setdefault(
            "coverage_label",
            "Padrão direto no Source Clays",
        )
        profiles["cms_source_clays"] = source_clays

    return profiles


def build_handbook_pdf_uri(mineral):
    """Construct the Handbook PDF URL candidate from a canonical mineral name."""
    mineral = mineral or {}
    candidate = clean_text(
        mineral.get("nome_cientifico_padronizado")
        or mineral.get("nome_en")
        or mineral.get("id")
    )
    if not candidate:
        return None
    slug = candidate.casefold().replace(" ", "")
    slug = slug.replace("'", "")
    slug = slug.replace(".", "")
    slug = slug.replace("/", "")
    slug = slug.replace("(", "")
    slug = slug.replace(")", "")
    slug = slug.replace(",", "")
    slug = slug.replace("–", "-").replace("—", "-")
    if not slug:
        return None
    return f"{HANDBOOK_PDF_BASE}/{slug}.pdf"


def build_generated_handbook_profile(profile):
    """Generate a Handbook-oriented fallback profile from family templates."""
    profile = profile or {}
    category = clean_text(profile.get("categoria_vocabulario"))
    family_id = clean_text(profile.get("familia_vocabulario"))
    canonical_name = clean_text(
        profile.get("nome_cientifico_padronizado")
        or profile.get("nome_en")
        or profile.get("nome")
    )
    if not canonical_name:
        return None

    uri = build_handbook_pdf_uri(profile)
    if not uri:
        return None

    family_template = deepcopy(HANDBOOK_FAMILY_REFERENCES.get(family_id) or {})

    facts = []
    for label, value in (
        ("Fórmula ideal", profile.get("formula_ideal")),
        ("Grupo mineralógico", profile.get("grupo_mineralogico")),
        ("Sistema cristalino", profile.get("sistema_cristalino")),
        ("Ambiente típico de formação", profile.get("ambiente_tipico_formacao")),
    ):
        cleaned = clean_text(value)
        if cleaned:
            facts.append({"label": label, "value": cleaned})

    if category == "species":
        return {
            "source_name": HANDBOOK_SOURCE,
            "uri": uri,
            "license": "Mineral Data Publishing; verificar permissoes da fonte original para reproducao ampliada.",
            "provenance": "Rota complementar gerada automaticamente pela Argiloteca a partir do nome científico padronizado do vocabulário controlado e síntese contextual da família mineralógica.",
            "summary": clean_text(family_template.get("summary"))
            or f"Fonte complementar de referência mineralógica para {canonical_name}, com potencial de dados cristalográficos, ocorrência, associações e distribuição.",
            "occurrence": clean_text(family_template.get("occurrence")),
            "association": clean_text(family_template.get("association")),
            "distribution": clean_text(family_template.get("distribution")),
            "facts": facts,
        }

    if category in {"group", "clay_material"}:
        return {
            "source_name": HANDBOOK_SOURCE,
            "uri": "https://handbookofmineralogy.org/pdf-search/",
            "license": "Mineral Data Publishing; verificar permissoes da fonte original para reproducao ampliada.",
            "provenance": "Rota complementar gerada automaticamente pela Argiloteca para consulta manual no PDF Search do Handbook of Mineralogy, combinada com síntese contextual da família mineralógica.",
            "summary": clean_text(family_template.get("summary"))
            or f"O Handbook of Mineralogy pode ser consultado como fonte complementar para espécies relacionadas a {canonical_name} por meio do PDF Search.",
            "occurrence": clean_text(family_template.get("occurrence")),
            "association": clean_text(family_template.get("association")),
            "distribution": clean_text(family_template.get("distribution")),
            "facts": facts,
        }

    if category in {"interstratified", "series"}:
        return {
            "source_name": HANDBOOK_SOURCE,
            "uri": "https://handbookofmineralogy.org/pdf-search/",
            "license": "Mineral Data Publishing; verificar permissoes da fonte original para reproducao ampliada.",
            "provenance": "Rota complementar gerada automaticamente pela Argiloteca com apoio da família mineralógica do vocabulário controlado.",
            "summary": clean_text(family_template.get("summary"))
            or f"O Handbook of Mineralogy pode servir como referência complementar para interpretar o contexto mineralógico de {canonical_name}.",
            "occurrence": clean_text(family_template.get("occurrence")),
            "association": clean_text(family_template.get("association")),
            "distribution": clean_text(family_template.get("distribution")),
            "facts": facts,
        }

    return None


def build_family_source_clays_profile(profile):
    """Generate a Source Clays family fallback with comparative coverage labels."""
    profile = profile or {}
    family_id = clean_text(profile.get("familia_vocabulario"))
    family_profile = deepcopy(SOURCE_CLAYS_FAMILY_REFERENCES.get(family_id) or {})
    if not family_profile:
        return None

    family_profile.setdefault("source_name", SOURCE_CLAYS_SOURCE)
    family_profile.setdefault("uri", "https://clays.org/sourceclays_data/")
    family_profile.setdefault("repository_uri", "https://www.clays.org/source-clays/")
    family_profile.setdefault("coverage_type", "comparative")
    family_profile.setdefault("coverage_label", "Material comparativo no Source Clays")
    family_profile.setdefault(
        "license",
        "Dados de referencia da Clay Minerals Society. Verificar a politica de uso e citacao da fonte original antes de redistribuicao ampliada.",
    )
    family_profile.setdefault(
        "provenance",
        "Rota complementar gerada automaticamente pela Argiloteca a partir da família mineralógica do vocabulário controlado.",
    )
    return family_profile


def build_family_earthchem_profile(profile):
    """Generate an EarthChem discovery block from the profile family context."""
    profile = profile or {}
    family_id = clean_text(profile.get("familia_vocabulario"))
    family_profile = deepcopy(EARTHCHEM_FAMILY_REFERENCES.get(family_id) or {})
    if not family_profile:
        return None

    canonical_name = clean_text(
        profile.get("nome_cientifico_padronizado")
        or profile.get("nome_en")
        or profile.get("nome")
        or profile.get("id")
    )
    category = clean_text(profile.get("categoria_vocabulario"))

    query_hint = canonical_name
    if category in {"group", "clay_material", "series", "interstratified"}:
        query_hint = clean_text(profile.get("nome_en")) or clean_text(profile.get("nome")) or canonical_name

    services = [
        {
            "label": "EarthChem Portal",
            "href": EARTHCHEM_PORTAL_URI,
            "facts": [
                {"label": "Uso recomendado", "value": "Busca federada em múltiplas bases geoquímicas e amostrais."},
                {"label": "Estratégia", "value": f"Começar por {query_hint} como termo principal e refinar por amostra, localidade ou contexto geológico."},
            ],
        },
        {
            "label": "PetDB 2.0",
            "href": EARTHCHEM_PETDB_URI,
            "facts": [
                {"label": "Uso recomendado", "value": "Explorar química, petrologia e metadados analíticos extraídos da literatura."},
                {"label": "Estratégia", "value": f"Usar {query_hint} em combinação com filtros de material, química e contexto petrográfico."},
            ],
        },
        {
            "label": "EarthChem Library",
            "href": EARTHCHEM_ECL_OVERVIEW_URI,
            "facts": [
                {"label": "Uso recomendado", "value": "Localizar datasets depositados, descrições de acervo e rotas de preservação/curadoria."},
                {"label": "Estratégia", "value": f"Buscar datasets e coleções relacionados a {query_hint}, especialmente quando houver publicação ou acervo associado."},
            ],
        },
    ]

    if family_id in {"pyrophyllite_talc", "pyrophyllite_talc_related", "layered_double_hydroxide", "short_range_order", "serpentine_group"}:
        services.append(
            {
                "label": "LEPR / TraceDs",
                "href": EARTHCHEM_LEPR_URI,
                "facts": [
                    {"label": "Uso recomendado", "value": "Consultar resultados experimentais, relações de fase e distribuição de elementos-traço."},
                    {"label": "Estratégia", "value": f"Usar esta rota quando {query_hint} aparecer em estudos experimentais, equilíbrios de fase ou partição mineral-fluido."},
                ],
            }
        )

    if family_id in {"pyrophyllite_talc", "pyrophyllite_talc_related", "layered_double_hydroxide", "short_range_order"}:
        services.append(
            {
                "label": "Experimental Petrology",
                "href": EARTHCHEM_EXPERIMENTAL_PETROLOGY_URI,
                "facts": [
                    {"label": "Uso recomendado", "value": "Acompanhar a comunidade e os requisitos curatoriais para datasets experimentais relevantes."},
                    {"label": "Estratégia", "value": f"Útil quando {query_hint} estiver ligado a síntese, estabilidade mineral ou dados laboratoriais especializados."},
                ],
            }
        )

    facts = []
    for label, value in (
        ("Escopo dos dados", family_profile.get("data_scope")),
        ("Termo sugerido para busca", query_hint),
    ):
        cleaned = clean_text(value)
        if cleaned:
            facts.append({"label": label, "value": cleaned})

    family_profile.setdefault("source_name", EARTHCHEM_SOURCE)
    family_profile.setdefault("uri", EARTHCHEM_PORTAL_URI)
    family_profile.setdefault("access_uri", EARTHCHEM_ACCESS_URI)
    family_profile.setdefault(
        "license",
        "EarthChem informa servicos de dados abertos; verificar a licenca especifica de cada dataset antes de redistribuicao ampliada.",
    )
    family_profile.setdefault(
        "provenance",
        "Rota complementar gerada automaticamente pela Argiloteca a partir da família mineralógica do vocabulário controlado e das portas oficiais de acesso do EarthChem.",
    )
    family_profile["query_hint"] = query_hint
    family_profile["facts"] = facts
    family_profile["samples"] = services
    return family_profile


def apply_multisource_fallbacks(profile):
    """Fill missing profile facts from curated and family-level source profiles."""
    profile = profile or {}
    source_profiles = profile.get("source_profiles") or {}
    handbook = source_profiles.get("handbook_mineralogy") or build_generated_handbook_profile(profile) or {}
    if handbook and "handbook_mineralogy" not in source_profiles:
        source_profiles["handbook_mineralogy"] = handbook

    if handbook:
        profile["formula_ideal"] = _first_nonempty(
            profile.get("formula_ideal"),
            handbook.get("formula_ideal"),
        )
        profile["sistema_cristalino"] = localize_crystal_system(
            _first_nonempty(profile.get("sistema_cristalino"), handbook.get("sistema_cristalino"))
        )
        profile["grupo_mineralogico"] = resolve_local_group_label(
            _first_nonempty(profile.get("grupo_mineralogico"), handbook.get("grupo_mineralogico")),
            profile.get("familia_vocabulario"),
        )
        profile["ambiente_tipico_formacao"] = _first_nonempty(
            profile.get("ambiente_tipico_formacao"),
            handbook.get("occurrence"),
        )
        profile["licenca_fonte"] = _first_nonempty(profile.get("licenca_fonte"), handbook.get("license"))
        profile["observacao_proveniencia"] = _first_nonempty(
            profile.get("observacao_proveniencia"),
            handbook.get("provenance"),
        )

    source_clays = source_profiles.get("cms_source_clays") or build_family_source_clays_profile(profile) or {}
    if source_clays and "cms_source_clays" not in source_profiles:
        source_profiles["cms_source_clays"] = source_clays

    earthchem = source_profiles.get("earthchem") or build_family_earthchem_profile(profile) or {}
    if earthchem and "earthchem" not in source_profiles:
        source_profiles["earthchem"] = earthchem

    profile["source_profiles"] = source_profiles
    return profile


def build_scientific_source_blocks(profile):
    """Format source profiles into UI blocks for Handbook, Source Clays and EarthChem."""
    profile = profile or {}
    blocks = []
    source_profiles = profile.get("source_profiles") or {}

    handbook = source_profiles.get("handbook_mineralogy") or {}
    if handbook:
        facts = list(handbook.get("facts") or [])
        for label, key in (
            ("Ocorrência", "occurrence"),
            ("Associações", "association"),
            ("Distribuição", "distribution"),
            ("Origem do nome", "name_origin"),
            ("Química", "chemistry"),
            ("Difração de raios X", "xray_powder_pattern"),
        ):
            value = clean_text(handbook.get(key))
            if value:
                marker = (label, normalize_lookup_key(value))
                existing = {(item.get("label"), normalize_lookup_key(item.get("value"))) for item in facts}
                if marker not in existing:
                    facts.append({"label": label, "value": value})

        blocks.append(
            {
                "key": "handbook_mineralogy",
                "title": HANDBOOK_SOURCE,
                "summary": clean_text(handbook.get("summary"))
                or "Ficha mineralógica complementar com dados cristalográficos, ocorrência e distribuição.",
                "href": clean_text(handbook.get("uri")),
                "href_label": "Abrir ficha do Handbook",
                "license": clean_text(handbook.get("license")),
                "provenance": clean_text(handbook.get("provenance")),
                "facts": facts,
                "samples": [],
            }
        )

    source_clays = source_profiles.get("cms_source_clays") or {}
    if source_clays:
        samples = []
        for sample in source_clays.get("samples") or []:
            if not isinstance(sample, dict):
                continue
            sample_facts = []
            for label, key in (
                ("Tipo", "availability"),
                ("Origem", "origin"),
                ("Localização", "location"),
                ("Química", "chemistry"),
                ("CEC", "cec"),
                ("Área superficial", "surface_area"),
                ("Densidade", "density"),
                ("Umidade", "moisture_content"),
                ("Análise térmica", "thermal_analysis"),
                ("Espectroscopia no IV", "infrared_spectroscopy"),
                ("Estrutura", "structure"),
                ("Notas", "notes"),
            ):
                value = clean_text(sample.get(key))
                if value:
                    sample_facts.append({"label": label, "value": value})
            samples.append(
                {
                    "code": clean_text(sample.get("code")),
                    "label": clean_text(sample.get("label")),
                    "facts": sample_facts,
                }
            )

        facts = []
        coverage_label = clean_text(source_clays.get("coverage_label"))
        if coverage_label:
            facts.append({"label": "Cobertura curatorial", "value": coverage_label})

        blocks.append(
            {
                "key": "cms_source_clays",
                "title": SOURCE_CLAYS_SOURCE,
                "summary": clean_text(source_clays.get("summary"))
                or "Materiais de referência laboratoriais da Clay Minerals Society relacionados a este argilomineral.",
                "badge": coverage_label,
                "href": clean_text(source_clays.get("uri")),
                "href_label": "Abrir dados dos Source Clays",
                "secondary_href": clean_text(source_clays.get("repository_uri")),
                "secondary_href_label": "Abrir repositório Source Clays",
                "license": clean_text(source_clays.get("license")),
                "provenance": clean_text(source_clays.get("provenance")),
                "facts": facts,
                "samples": samples,
            }
        )

    earthchem = source_profiles.get("earthchem") or {}
    if earthchem:
        facts = list(earthchem.get("facts") or [])
        samples = []
        for sample in earthchem.get("samples") or []:
            if not isinstance(sample, dict):
                continue
            sample_facts = []
            for fact in sample.get("facts") or []:
                if not isinstance(fact, dict):
                    continue
                label = clean_text(fact.get("label"))
                value = clean_text(fact.get("value"))
                if label and value:
                    sample_facts.append({"label": label, "value": value})
            samples.append(
                {
                    "label": clean_text(sample.get("label")),
                    "code": clean_text(sample.get("code")),
                    "href": clean_text(sample.get("href")),
                    "facts": sample_facts,
                }
            )
        for label, key in (
            ("Escopo dos dados", "data_scope"),
            ("Termo sugerido para busca", "query_hint"),
        ):
            value = clean_text(earthchem.get(key))
            if value:
                marker = (label, normalize_lookup_key(value))
                existing = {(item.get("label"), normalize_lookup_key(item.get("value"))) for item in facts}
                if marker not in existing:
                    facts.append({"label": label, "value": value})

        blocks.append(
            {
                "key": "earthchem",
                "title": EARTHCHEM_SOURCE,
                "summary": clean_text(earthchem.get("summary"))
                or "Fonte complementar para localizar datasets geoquímicos, amostras e metadados petrológicos relacionados a este argilomineral.",
                "href": clean_text(earthchem.get("uri")) or EARTHCHEM_PORTAL_URI,
                "href_label": "Abrir portal EarthChem",
                "secondary_href": clean_text(earthchem.get("access_uri")) or EARTHCHEM_ACCESS_URI,
                "secondary_href_label": "Abrir visão geral de acesso",
                "license": clean_text(earthchem.get("license")),
                "provenance": clean_text(earthchem.get("provenance")),
                "facts": facts,
                "samples": samples,
            }
        )

    return blocks


def generate_short_description(mineral):
    """Build a concise scientific summary from structured metadata."""
    mineral = mineral or {}
    name = resolve_mineral_name(mineral)
    if not name:
        return None

    sentences = [f"{name}."]

    class_structural = resolve_structural_class(mineral.get("id") or mineral.get("slug"), mineral)
    formula = clean_text(mineral.get("formula_ideal"))
    first_sentence_parts = []
    if class_structural:
        first_sentence_parts.append(class_structural)
    if formula:
        first_sentence_parts.append(f"fórmula ideal {formula}")
    if first_sentence_parts:
        sentences.append(", ".join(first_sentence_parts) + ".")

    crystal_system = localize_crystal_system(mineral.get("sistema_cristalino"))
    if crystal_system:
        sentences.append(f"Sistema cristalino {lowercase_first(crystal_system)}.")

    group = resolve_mineral_group(mineral)
    subgrupo = clean_text(mineral.get("subgrupo_mineralogico"))
    has_structured_fact = any([class_structural, formula, crystal_system, group, subgrupo])
    if not has_structured_fact:
        return None

    if group:
        group_text = clean_text(group)
        lowered_group = lowercase_first(group_text)
        if lowered_group and lowered_group.startswith("grupo "):
            sentences.append(f"Pertence ao {lowered_group}.")
        else:
            sentences.append(f"Pertence ao grupo {lowered_group}.")

    if subgrupo:
        sentences.append(f"Incluído no subgrupo {lowercase_first(subgrupo)}.")

    reference = resolve_external_reference(mineral)
    if reference["source"]:
        sentences.append(f"Fonte: {reference['source']}.")

    return " ".join(sentences)


def resolve_short_description(mineral):
    """Return curated short text or generate one from structured facts."""
    mineral = mineral or {}
    return clean_text(mineral.get("descricao_curta")) or generate_short_description(mineral)


def generate_classic_description(mineral):
    """Build a longer local descriptive text for the mineral profile page."""
    mineral = mineral or {}
    name = resolve_mineral_name(mineral)
    if not name:
        return None

    category = clean_text(mineral.get("categoria_vocabulario"))
    class_structural = resolve_structural_class(mineral.get("id") or mineral.get("slug"), mineral)
    formula = clean_text(mineral.get("formula_ideal"))
    crystal_system = localize_crystal_system(mineral.get("sistema_cristalino"))
    group = resolve_mineral_group(mineral)
    strunz = clean_text(mineral.get("classificacao_strunz"))
    dana = clean_text(mineral.get("classificacao_dana"))
    synonyms = clean_text(mineral.get("sinonimos"))
    reference = resolve_external_reference(mineral)
    has_structured_fact = any(
        [
            class_structural,
            formula,
            crystal_system,
            group,
            strunz,
            dana,
            synonyms,
        ]
    )
    if not has_structured_fact:
        if reference["source"] and reference["uri"]:
            return (
                f"{name} possui vinculo local com a referencia {reference['source']} "
                f"({reference['uri']}), mas os campos descritivos ainda aguardam extracao ou curadoria tecnica."
            )
        if reference["source"]:
            return (
                f"{name} possui vinculo local com a referencia {reference['source']}, "
                "mas os campos descritivos ainda aguardam extracao ou curadoria tecnica."
            )
        return None

    first_parts = []
    if class_structural:
        first_parts.append(class_structural)
    elif category:
        first_parts.append(category.replace("_", " "))

    if formula:
        first_parts.append(f"fórmula ideal {formula}")
    if crystal_system:
        first_parts.append(f"sistema cristalino {lowercase_first(crystal_system)}")

    first_sentence = f"{name} é um argilomineral"
    if first_parts:
        first_sentence += " de " + ", ".join(first_parts)
    first_sentence += "."

    third_parts = []
    if strunz:
        third_parts.append(f"classificação Strunz {strunz}")
    if dana:
        third_parts.append(f"classificação Dana {dana}")
    if synonyms:
        third_parts.append(f"sinônimos registrados: {synonyms}")
    third_sentence = ""
    if third_parts:
        third_sentence = "Como apoio de curadoria local, o perfil reúne " + "; ".join(third_parts) + "."

    source_sentence = ""
    if reference["source"] and reference["uri"]:
        source_sentence = (
            f"Esta descrição expandida é uma síntese local da Argiloteca baseada na referência {reference['source']} "
            f"e no vínculo rastreável {reference['uri']}."
        )
    elif reference["source"]:
        source_sentence = (
            f"Esta descrição expandida é uma síntese local da Argiloteca baseada na referência {reference['source']}."
        )

    paragraphs = [first_sentence]
    if third_sentence:
        paragraphs.append(third_sentence)
    if source_sentence:
        paragraphs.append(source_sentence)
    return "\n\n".join(paragraphs)


def build_mineral_profile(term):
    """Resolve a mineral term into a local Argiloteca profile payload.

    A funcao centraliza vocabulario, sementes curadas, fontes complementares,
    aliases, comunidade e imagem reutilizavel para consumo por rotas/templates.
    """
    raw_term = clean_text(term)
    if not raw_term:
        return None

    lookup_id = _mineral_lookup_index().get(normalize_lookup_key(raw_term))
    if not lookup_id:
        return None

    seeds = load_curated_mindat_seeds()
    vocabulary = load_argilominerais_vocabulary()
    seed = deepcopy(seeds.get(lookup_id) or {})
    vocab = deepcopy(vocabulary.get(lookup_id) or {})
    titles = vocab.get("title") or {}
    props = vocab.get("props") or {}

    profile = {}
    profile.update(seed)
    profile["id"] = lookup_id
    profile["slug"] = lookup_id
    profile["nome_pt"] = clean_text(seed.get("nome_pt")) or clean_text(titles.get("pt"))
    profile["nome_en"] = clean_text(seed.get("nome_en")) or clean_text(titles.get("en"))
    profile["nome"] = clean_text(seed.get("nome")) or profile["nome_pt"] or profile["nome_en"]
    profile["nome_cientifico_padronizado"] = (
        clean_text(seed.get("nome_cientifico_padronizado")) or profile["nome_en"] or profile["nome"]
    )
    profile["categoria_vocabulario"] = clean_text(seed.get("categoria_vocabulario")) or clean_text(props.get("category"))
    profile["familia_vocabulario"] = clean_text(seed.get("familia_vocabulario")) or clean_text(props.get("family"))
    profile["broader_vocabulario"] = clean_text(seed.get("broader_vocabulario")) or clean_text(props.get("broader"))
    profile["broader"] = profile["broader_vocabulario"]
    profile["classe_estrutural"] = resolve_structural_class(lookup_id, profile)
    profile["grupo_mineralogico"] = resolve_local_group_label(
        profile.get("grupo_mineralogico") or profile.get("grupo"),
        profile.get("familia_vocabulario"),
    )
    profile["sistema_cristalino"] = localize_crystal_system(profile.get("sistema_cristalino"))
    profile["observacao_proveniencia"] = resolve_provenance_note(profile)
    profile["source_profiles"] = build_source_profiles(lookup_id)
    profile = apply_multisource_fallbacks(profile)

    profile = enrich_mineral_semantics(profile, identifier=lookup_id)
    profile["classic_description"] = clean_text(profile.get("descricao_classica")) or generate_classic_description(profile)
    profile["community_slug"] = profile.get("community_slug") or resolve_community_slug(
        profile.get("grupo_mineralogico"),
        profile.get("grupo"),
        profile.get("familia_vocabulario"),
    )
    profile["reference"] = resolve_external_reference(profile)
    profile["aliases"] = clean_list(
        [
            profile.get("nome"),
            profile.get("nome_pt"),
            profile.get("nome_en"),
            profile.get("nome_cientifico_padronizado"),
            profile.get("broader"),
            profile.get("sinonimos"),
        ]
    )
    profile["curatorial_facts"] = build_curatorial_facts(profile)
    profile["referencias_mindat_itens"] = split_mindat_reference_list(profile.get("referencias_mindat"))
    profile["scientific_source_blocks"] = build_scientific_source_blocks(profile)
    profile["license_entries"] = build_license_entries(profile)
    profile["reusable_image"] = build_reusable_image_profile(lookup_id, profile)
    return profile


@lru_cache(maxsize=1)
def build_authorized_mineral_catalog():
    """Build the compact authorized mineral catalog used by menus and APIs."""
    items = []
    for identifier in sorted(load_argilominerais_vocabulary()):
        profile = build_mineral_profile(identifier)
        if not profile:
            continue
        items.append(
            {
                "id": profile.get("id") or identifier,
                "slug": profile.get("slug") or identifier,
                "nome": profile.get("nome") or profile.get("nome_cientifico_padronizado") or identifier,
                "nome_pt": profile.get("nome_pt"),
                "nome_en": profile.get("nome_en"),
                "nome_cientifico_padronizado": profile.get("nome_cientifico_padronizado"),
                "grupo_mineralogico": profile.get("grupo_mineralogico"),
                "classe_estrutural": profile.get("classe_estrutural"),
                "descricao_curta": profile.get("descricao_curta"),
                "community_slug": profile.get("community_slug"),
                "reusable_image": deepcopy(profile.get("reusable_image") or {}),
            }
        )

    items.sort(
        key=lambda item: normalize_lookup_key(
            item.get("nome_pt")
            or item.get("nome")
            or item.get("nome_cientifico_padronizado")
            or item.get("id")
        )
        or ""
    )
    return items


def build_invenio_subjects(mineral, identifier=None):
    """Build standard Invenio metadata.subjects entries from mineral metadata."""
    mineral = mineral or {}
    subjects = []
    seen = set()

    def add_subject(label):
        """
        Executa uma etapa coesa do fluxo do módulo, mantendo contratos de entrada e saída usados pelo painel Argiloteca.
        
        Args:
            label: Valor de entrada consumido por esta etapa do fluxo.
        Returns:
            Resultado produzido pela etapa, quando aplicável ao contrato do chamador.
        Raises:
            Exception: Propaga erros das dependências quando a validação ou o processamento falha.
        """
        subject = clean_text(label)
        key = (subject or "").casefold()
        if not subject or key in seen:
            return
        subjects.append({"subject": subject})
        seen.add(key)

    preferred_name = clean_text(mineral.get("nome")) or resolve_mineral_name(mineral)
    canonical_name = clean_text(mineral.get("nome_cientifico_padronizado"))

    add_subject(preferred_name)
    if canonical_name and canonical_name.casefold() != (preferred_name or "").casefold():
        add_subject(canonical_name)

    return subjects


def resolve_group_community_slug(group_value):
    """Map a mineralogical group label or id to an Argiloteca community slug."""
    key = normalize_lookup_key(group_value)
    if not key:
        return None
    for candidate, slug in COMMUNITY_SLUG_BY_GROUP_KEY.items():
        if normalize_lookup_key(candidate) == key:
            return slug
    return None


def derive_community_slugs_from_minerals(minerals):
    """Return ordered community slugs derived from mineralogical groups."""
    slugs = []
    seen = set()

    for mineral in minerals or []:
        mineral = mineral or {}
        for candidate in (
            mineral.get("grupo_mineralogico"),
            mineral.get("grupo"),
            mineral.get("subgrupo_mineralogico"),
        ):
            slug = resolve_group_community_slug(candidate)
            if slug and slug not in seen:
                slugs.append(slug)
                seen.add(slug)

    return slugs


def enrich_mineral_semantics(mineral, identifier=None):
    """Return a semantically enriched mineral payload without mutating input."""
    if isinstance(mineral, dict):
        mineral = deepcopy(mineral)
    else:
        legacy_text = clean_text(mineral)
        mineral = {"nome": legacy_text} if legacy_text else {}
    preferred_name = resolve_mineral_name(mineral)
    group = resolve_mineral_group(mineral)
    reference = resolve_external_reference(mineral)

    if preferred_name and not clean_text(mineral.get("nome")):
        mineral["nome"] = preferred_name

    if group and not clean_text(mineral.get("grupo")):
        mineral["grupo"] = group

    short_description = resolve_short_description(mineral)
    if short_description and not clean_text(mineral.get("descricao_curta")):
        mineral["descricao_curta"] = short_description

    if reference["source"] and not clean_text(mineral.get("external_source")):
        mineral["external_source"] = reference["source"]

    if reference["id"] and not clean_text(mineral.get("external_id")):
        mineral["external_id"] = reference["id"]

    if reference["uri"] and not clean_text(mineral.get("external_uri")):
        mineral["external_uri"] = reference["uri"]

    mineral["subjects"] = build_invenio_subjects(mineral, identifier=identifier)
    mineral["community_slug"] = resolve_community_slug(
        group,
        mineral.get("grupo"),
        mineral.get("familia_vocabulario"),
    )
    return mineral
