# turns analysis.html (the nbconvert export) into the styled portfolio.html
# run after: jupyter nbconvert --to html analysis.ipynb

from pathlib import Path
from bs4 import BeautifulSoup

REPO_URL = "https://github.com/bridgetmunoz23/schedule_python"

CUSTOM_CSS = """
<style>
  body {
    font-family: "Times New Roman", Times, Georgia, serif;
    background: #ffffff;
    color: #1f2937;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  .jp-Notebook > main {
    max-width: 880px;
    margin: 0 auto;
    padding: 0;
  }

  /* ---- Sections: alternating tints + generous padding so each reads
     like a new chapter ---- */
  .portfolio-section {
    padding: 56px 48px;
    margin: 0;
  }
  .portfolio-section:nth-of-type(odd)  { background: #ffffff; }
  .portfolio-section:nth-of-type(even) { background: #f8f9fa; }

  /* ---- Main title ---- */
  h1 {
    font-size: 2.7em;
    font-weight: 800;
    letter-spacing: -0.025em;
    line-height: 1.1;
    color: #142a47;
    margin: 0 0 0.7em 0;
  }

  /* ---- Section headings: large, navy, accent bar marks each transition ---- */
  h2 {
    font-size: 1.8em;
    font-weight: 700;
    letter-spacing: -0.015em;
    line-height: 1.25;
    color: #1f3a5f;
    margin: 0 0 0.9em 0;
    padding: 2px 0 2px 16px;
    border-left: 4px solid #2c6cb0;
  }

  /* ---- Subheadings: medium weight, clearly subordinate ---- */
  h3 {
    font-size: 1.25em;
    font-weight: 600;
    color: #33475b;
    letter-spacing: -0.01em;
    margin: 2em 0 0.6em 0;
  }

  /* ---- Body text ---- */
  p, ul, ol, li {
    font-size: 16px;
    line-height: 1.6;
    color: #1f2937;
  }
  p { margin: 0 0 1.1em 0; }
  a.anchor-link { display: none; }

  /* ---- Callouts: reserved for emphasis lead-in paragraphs only
     (e.g. "Reading the coefficients:") ---- */
  .callout {
    background: #eef4fb;
    border-left: 4px solid #2c6cb0;
    border-radius: 4px;
    padding: 14px 18px;
    margin: 1.3em 0 1.5em 0;
  }
  .callout strong { color: #1f3a5f; }
  .callout > p:first-child { margin-top: 0; }

  /* ---- Section Four metric explorer ---- */
  .metric-explorer { margin: 6px 0 4px; }
  .metric-pick {
    font-weight: bold;
    color: #1f3a5f;
    font-size: 16px;
    display: inline-block;
    margin-bottom: 12px;
  }
  .metric-pick select {
    font-family: inherit;
    font-size: 15px;
    padding: 5px 10px;
    border: 1px solid #2c6cb0;
    border-radius: 6px;
    color: #1f3a5f;
    background: white;
    cursor: pointer;
  }
  .metric-imgs img { max-width: 100%; height: auto; }

  /* ---- Figure captions / footnotes ---- */
  .figure-note {
    font-size: 12px !important;
    color: #6b7280;
    font-style: italic;
    line-height: 1.45;
    margin: -8px 0 2.4em 0;
  }
  .figure-note strong { color: #4b5563; font-style: normal; }

  .callout > :last-child { margin-bottom: 0; }
  .callout ul { margin: 0.4em 0 0 0; }

  /* ---- Cells: no box around prose; breathing room above outputs ---- */
  .jp-Cell { margin: 0; padding: 0; }
  .jp-MarkdownCell .jp-InputArea,
  .jp-MarkdownCell .jp-RenderedMarkdown {
    background: none;
    border: none;
    box-shadow: none;
    padding: 0;
  }
  .jp-Cell-outputWrapper { margin-top: 24px; }
  .jp-OutputArea-output {
    overflow-x: auto;            /* wide tables/charts scroll instead of breaking layout */
    -webkit-overflow-scrolling: touch;
  }
  .jp-OutputArea-output img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 8px auto;
  }

  /* ---- De-emphasize In[N]:/Out[N]: prompts and reclaim the gutter ---- */
  .jp-InputPrompt, .jp-OutputPrompt {
    font-size: 11px;
    color: #b3b9c2;
    font-weight: 400;
    min-width: 0;
    padding-right: 8px;
  }

  /* ---- Code input (hidden unless its section has .show-code) ---- */
  .jp-CodeCell .jp-InputArea {
    background: #f4f4ee;
    border-radius: 6px;
    border: 1px solid #e6e6dc;
  }
  .portfolio-section .jp-CodeCell .jp-Cell-inputWrapper { display: none; }
  .portfolio-section.show-code .jp-CodeCell .jp-Cell-inputWrapper { display: block; }
  .code-toggle {
    display: inline-block;
    background: white;
    border: 1px solid #2c6cb0;
    color: #2c6cb0;
    padding: 5px 14px;
    border-radius: 18px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    font-family: inherit;
    margin: 4px 0 20px;
    transition: background 0.15s, color 0.15s;
  }
  .code-toggle:hover {
    background: #2c6cb0;
    color: white;
  }

  /* ---- Tables: colored header row, alternating row shading ---- */
  table.dataframe, .jp-RenderedMarkdown table {
    border-collapse: collapse !important;
    margin: 22px 0 !important;
    font-size: 14.5px !important;
    width: auto !important;
    border: none !important;
  }
  table.dataframe thead th, .jp-RenderedMarkdown table thead th {
    background: #1f3a5f !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    text-align: left !important;
    padding: 9px 15px !important;
    border: none !important;
  }
  table.dataframe tbody td, table.dataframe tbody th,
  .jp-RenderedMarkdown table tbody td, .jp-RenderedMarkdown table tbody th {
    padding: 8px 15px !important;
    border: none !important;
    border-bottom: 1px solid #e6e9ed !important;
    text-align: left !important;
  }
  table.dataframe tbody tr:nth-child(even),
  .jp-RenderedMarkdown table tbody tr:nth-child(even) {
    background: #f1f4f8 !important;
  }

  /* ---- Footer ---- */
  .portfolio-footer {
    max-width: 880px;
    margin: 0 auto;
    padding: 40px 48px 48px;
    border-top: 1px solid #d8d8cf;
    color: #555;
    font-size: 14px;
    text-align: center;
  }
  .portfolio-footer a {
    color: #2c6cb0;
    text-decoration: none;
    border-bottom: 1px solid #2c6cb0;
    font-weight: 500;
  }
  .portfolio-footer a:hover {
    background: #2c6cb0;
    color: white;
  }

  /* ---- Mobile / small screens ---- */
  @media (max-width: 640px) {
    .portfolio-section { padding: 28px 18px; }
    h1 { font-size: 1.9em; }
    h2 { font-size: 1.35em; padding-left: 12px; }
    h3 { font-size: 1.1em; }
    p, ul, ol, li { font-size: 15.5px; }
    .callout { padding: 12px 14px; }
    table.dataframe, .jp-RenderedMarkdown table { font-size: 12.5px !important; }
    .portfolio-footer { padding: 32px 18px 40px; }
  }
</style>
"""

TOGGLE_SCRIPT = """
<script>
  document.querySelectorAll('.code-toggle').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var section = btn.closest('.portfolio-section');
      var on = section.classList.toggle('show-code');
      btn.textContent = on ? 'Hide code' : 'Show code';
    });
  });
</script>
"""

FOOTER_HTML = f"""
<div class="portfolio-footer">
  Built with Python, pandas, scikit-learn, matplotlib, and seaborn.<br>
  Schedule and game-log data via <a href="https://github.com/swar/nba_api">nba_api</a>.<br><br>
  <a href="{REPO_URL}">View the source code on GitHub &rarr;</a>
</div>
"""


def _mark_callouts(soup):
    # paragraphs that start with a bold "label:" get the blue callout box
    for p in soup.select(".jp-RenderedMarkdown p"):
        child = next((c for c in p.children if getattr(c, "name", None)), None)
        if child is not None and child.name == "strong" \
                and child.get_text(strip=True).endswith(":"):
            p["class"] = (p.get("class") or []) + ["callout"]


def _wrap_topics_callout(soup):
    # put the Topics of Interest header + its list in a callout box
    for p in soup.select(".jp-RenderedMarkdown p"):
        child = next((c for c in p.children if getattr(c, "name", None)), None)
        if child is not None and child.name == "strong" \
                and child.get_text(strip=True) == "Topics of Interest":
            ul = p.find_next_sibling("ul")
            box = soup.new_tag("div", **{"class": "callout"})
            p.insert_before(box)
            box.append(p.extract())
            if ul is not None:
                box.append(ul.extract())
            break


def build(src="analysis.html", dst="portfolio.html"):
    soup = BeautifulSoup(Path(src).read_text(), "html.parser")
    soup.head.append(BeautifulSoup(CUSTOM_CSS, "html.parser"))

    main = soup.find(class_="jp-Notebook").find("main")
    cells = [c for c in main.children if getattr(c, "name", None) == "div"
             and "jp-Cell" in (c.get("class") or [])]

    # split cells into sections at each H2 (intro is everything before the first)
    groups = []
    current = []
    for cell in cells:
        if cell.find("h2") and current:
            groups.append(current)
            current = [cell]
        else:
            current.append(cell)
    if current:
        groups.append(current)

    # wrap each group in a <section>, add a Show code button if it has code
    for grp in groups:
        first = grp[0]
        section = soup.new_tag("section", **{"class": "portfolio-section"})
        first.insert_before(section)
        for c in grp:
            section.append(c.extract())

        has_code = any("jp-CodeCell" in (c.get("class") or []) for c in grp)
        if has_code:
            btn = soup.new_tag("button", **{"class": "code-toggle"})
            btn.string = "Show code"
            # Insert after the heading cell (first cell in the section)
            grp[0].insert_after(btn)

    _mark_callouts(soup)
    _wrap_topics_callout(soup)

    soup.body.append(BeautifulSoup(FOOTER_HTML, "html.parser"))
    soup.body.append(BeautifulSoup(TOGGLE_SCRIPT, "html.parser"))

    Path(dst).write_text(str(soup))
    print(f"wrote {dst} ({Path(dst).stat().st_size // 1024} KB)")
    print(f"reminder: replace REPO_URL in {Path(__file__).name} once the GitHub repo exists.")


if __name__ == "__main__":
    build()
