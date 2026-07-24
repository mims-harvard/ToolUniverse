import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "setup_keys_server", REPO / "plugin" / "scripts" / "setup_keys_server.py"
)
srv = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(srv)

CATALOG = [
    {"name": "OMIM_API_KEY", "requirement": "optional", "type": "secret",
     "domain": "Genomics & Variants", "register_url": "https://omim.org/api",
     "purpose": "Look up Mendelian disease records.", "without": "OMIM tools return no data without it."},
    {"name": "ESM_MCP_SERVER_HOST", "requirement": "required", "type": "endpoint",
     "domain": "Models & Infrastructure", "register_url": "https://forge.evolutionaryscale.ai/",
     "purpose": "URL of a self-hosted ESM MCP server.", "without": "Leave blank unless you self-host."},
]


def test_render_form_shows_names_links_and_masks_existing():
    html = srv.render_form(CATALOG, existing={"OMIM_API_KEY": "sk-secret-1234"}, token="tok")
    assert "OMIM_API_KEY" in html
    assert "https://omim.org/api" in html
    assert "tok" in html
    assert "****1234" in html
    assert "sk-secret-1234" not in html


def test_render_form_groups_by_domain_with_purpose_and_without():
    html = srv.render_form(CATALOG, existing={}, token="tok")
    assert "Genomics &amp; Variants" in html
    assert "Models &amp; Infrastructure" in html
    assert "Look up Mendelian disease records." in html
    assert "Leave blank unless you self-host." in html
    assert html.count('class="card"') == 2
    assert "Required keys" not in html
    assert "Service Endpoints" not in html


def test_compute_updates_sets_and_clears():
    names = ["OMIM_API_KEY", "ESM_MCP_SERVER_HOST"]
    form = {"OMIM_API_KEY": ["new-val"], "clear__ESM_MCP_SERVER_HOST": ["1"], "token": ["tok"]}
    assert srv.compute_updates(form, names) == {"OMIM_API_KEY": "new-val", "ESM_MCP_SERVER_HOST": ""}


def test_compute_updates_blank_is_noop():
    form = {"OMIM_API_KEY": [""], "token": ["tok"]}
    assert srv.compute_updates(form, ["OMIM_API_KEY"]) == {}


def test_check_token():
    assert srv.check_token("abc", "abc") is True
    assert srv.check_token("abc", "xyz") is False
    assert srv.check_token("abc", None) is False
