import json

import pytest

import relevant_pages as rp


@pytest.mark.parametrize("raw, title", [
    ("Emmanuel_Macron", "Emmanuel_Macron"),
    ("https://fr.wikipedia.org/wiki/Nathalie_Arthaud", "Nathalie_Arthaud"),
    ("https://fr.wikipedia.org/wiki/Jean-Luc_M%C3%A9lenchon", "Jean-Luc_Mélenchon"),
    ("/wiki/Cinquième_République_(France)", "Cinquième_République_(France)"),
    ("fr.wikipedia.org/wiki/Python (langage)", "Python_(langage)"),
    ("CDU/CSU", "CDU/CSU"),                     # un "/" dans un titre n'est pas une URL
    ("écologie", "Écologie"),                   # 1re lettre en majuscule comme MediaWiki
])
def test_normalize_title(raw, title):
    assert rp.normalize_title(raw) == title


@pytest.mark.parametrize("title, is_date", [
    ("1949", True), ("-1750", True), ("16_mai", True), ("1er_avril", True),
    ("Novembre_1944", True), ("Années_1990", True), ("XXe_siècle", True),
    ("Mai_68", False), ("Crise_de_mai_1958", False), ("2017_en_France", False),
    ("8_mai_1945", False), ("11_septembre_2001", False),
    ("Emmanuel_Macron", False),
])
def test_is_date_title(title, is_date):
    assert rp.is_date_title(title) is is_date


@pytest.fixture
def pages_file(tmp_path):
    path = tmp_path / "politic_related_pages.json"
    path.write_text(json.dumps({"politic_related_pages": {
        "https://fr.wikipedia.org/wiki/Marine_Le_Pen": 0.97,
        "Marine_Le_Pen": 0.99,
        "Groupe_PSA": 0.77,
        "1949": 0.95,
        "Mai_68": 0.92,
    }}), encoding="utf-8")
    return str(path)


def test_load_relevant_pages(pages_file):
    pages = rp.load_relevant_pages(pages_file, min_score=0.9)
    assert pages == {"Marine_Le_Pen": 0.99, "Mai_68": 0.92}


def test_load_relevant_pages_keep_all(pages_file):
    pages = rp.load_relevant_pages(pages_file, min_score=0.0, drop_dates=False)
    assert set(pages) == {"Marine_Le_Pen", "Groupe_PSA", "1949", "Mai_68"}


def test_load_seed_pages(tmp_path):
    (tmp_path / "candidate.csv").write_text(
        "ID;Name;Url;Type;WikiExist\n"
        "16;Jean-Luc_M%C3%A9lenchon;https://fr.wikipedia.org/wiki/Jean-Luc_M%C3%A9lenchon;Candidate;1\n"
        "12;Selma_Labib;;Candidate;0\n", encoding="utf-8")
    (tmp_path / "pages.csv").write_text(
        "ID;Name;Url;Type;Category;Portal\n"
        "5;x;https://fr.wikipedia.org/wiki/Catégorie:Santé_en_France;Link List;1;0\n"
        "16;x;https://fr.wikipedia.org/wiki/Pain_au_chocolat;Unrelated;0;0\n"
        "17;x;https://fr.wikipedia.org/wiki/Cinqui%C3%A8me_R%C3%A9publique_(France);0;0\n",
        encoding="utf-8")
    assert rp.load_seed_pages(str(tmp_path)) == {
        "Jean-Luc_Mélenchon": 1.0, "Cinquième_République_(France)": 1.0}


def test_default_pages_without_submodule(monkeypatch, tmp_path):
    monkeypatch.setattr(rp, "DEFAULT_PAGES_FILE", str(tmp_path / "absent.json"))
    assert rp.default_pages() == {}


@pytest.mark.skipif(not rp.os.path.exists(rp.DEFAULT_PAGES_FILE),
                    reason="submodule non initialisé")
def test_real_submodule_file():
    pages = rp.default_pages()
    assert len(pages) > 1000
    assert all(0.9 <= s <= 1.0 for s in pages.values())
    # absents du fichier du crawler, récupérés via les pages de départ
    assert "Jean-Luc_Mélenchon" in pages and "Éric_Zemmour" in pages
    assert "Pain_au_chocolat" not in pages
    assert not any(rp.is_date_title(t) for t in pages)
