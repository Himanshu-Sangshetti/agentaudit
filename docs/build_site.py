"""Render docs/WRITEUP.md into docs/site/index.html (a self-styled page; figures are sibling files)."""
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
md = (ROOT / "WRITEUP.md").read_text()
md = md.replace("](figures/", "](figures/").replace("](../bench/", "](https://github.com/Himanshu-Sangshetti/agentaudit/blob/main/bench/")
md = md.replace("](REPORT.md)", "](https://github.com/Himanshu-Sangshetti/agentaudit/blob/main/docs/REPORT.md)")
mermaid = re.search(r"```mermaid\n(.*?)```", md, re.S)
md = md.replace(mermaid.group(0), "MERMAIDBLOCK")
body = markdown.markdown(md, extensions=["tables", "fenced_code"])
body = body.replace("<p>MERMAIDBLOCK</p>", f'<figure class="diagram"><pre class="mermaid">{mermaid.group(1)}</pre></figure>')
body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', r'<figure class="chart"><img alt="\1" src="\2"></figure>', body)
body = re.sub(r"<table>", '<div class="table-wrap"><table>', body).replace("</table>", "</table></div>")
TEMPLATE = (ROOT / "site_template.html").read_text()
(ROOT / "site/index.html").write_text(TEMPLATE.replace("{{BODY}}", body))
print("wrote docs/site/index.html")
