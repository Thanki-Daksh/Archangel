"""VaultBuilder — generates Obsidian-compatible Markdown notes with YAML frontmatter, wikilinks, and .canvas graphs."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from archangel.models import RawPost

logger = logging.getLogger(__name__)


class VaultBuilder:
    """Manages Obsidian Markdown vault files, wikilinks, and .canvas visual graph generation."""

    def __init__(self, vault_dir: Optional[Path] = None) -> None:
        self.vault_dir = vault_dir or Path("data/vault")
        self.leads_dir = self.vault_dir / "Leads"
        self.companies_dir = self.vault_dir / "Companies"
        self.tech_dir = self.vault_dir / "Technologies"
        self.canvases_dir = self.vault_dir / "Canvases"
        self._init_dirs()

    def _init_dirs(self) -> None:
        for d in [self.leads_dir, self.companies_dir, self.tech_dir, self.canvases_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def build_lead_note(
        self,
        post: RawPost,
        raw_post_id: int,
        status: str = "discovered",
        enrichment: Optional[Dict[str, Any]] = None,
        drafts: Optional[Dict[str, str]] = None,
    ) -> Path:
        company = (enrichment.get("company_name") if enrichment else "") or "Unknown"
        domain = (enrichment.get("domain") if enrichment else "") or "N/A"
        tech_list = (enrichment.get("detected_tech") if enrichment else [])

        tech_wikilinks = [f"[[Tech:{t}]]" for t in tech_list]
        company_wikilink = f"[[Company:{company}]]" if company != "Unknown" else "None"

        file_name = f"Lead-{raw_post_id}.md"
        file_path = self.leads_dir / file_name

        frontmatter = (
            f"---\n"
            f"id: {raw_post_id}\n"
            f"source: \"{post.source}\"\n"
            f"author: \"{post.author}\"\n"
            f"status: \"{status}\"\n"
            f"domain: \"{domain}\"\n"
            f"company: \"{company}\"\n"
            f"tags:\n" + "".join(f"  - {t}\n" for t in tech_list) +
            f"---\n\n"
        )

        content = (
            f"# Lead #{raw_post_id} — {post.source.capitalize()}\n\n"
            f"**Status:** `{status}`  \n"
            f"**Company:** {company_wikilink}  \n"
            f"**Technologies:** {', '.join(tech_wikilinks) if tech_wikilinks else 'None'}  \n"
            f"**Source URL:** [{post.url}]({post.url})  \n\n"
            f"## Raw Content\n\n> {post.content}\n\n"
        )

        if drafts:
            content += "## Outreach Drafts\n\n"
            for channel, draft_text in drafts.items():
                content += f"### {channel.capitalize()} Draft\n```text\n{draft_text}\n```\n\n"

        content += (
            "## Dataview Summary\n\n"
            "```dataview\n"
            "TABLE status, company, source FROM \"Leads\"\n"
            "WHERE file.name = this.file.name\n"
            "```\n"
        )

        file_path.write_text(frontmatter + content, encoding="utf-8")

        # Also maintain company & tech index notes
        if company != "Unknown":
            self.build_company_note(company, raw_post_id)
        for t in tech_list:
            self.build_tech_note(t, raw_post_id)

        # Update visual canvas map
        self.build_pipeline_canvas()

        logger.debug("Wrote lead note %s", file_path)
        return file_path

    def build_company_note(self, company: str, lead_id: int) -> Path:
        file_path = self.companies_dir / f"Company-{company}.md"
        content = (
            f"# Company: {company}\n\n"
            f"## Linked Leads\n"
            f"- [[Lead-{lead_id}]]\n"
        )
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
            if f"[[Lead-{lead_id}]]" not in existing:
                existing += f"- [[Lead-{lead_id}]]\n"
                file_path.write_text(existing, encoding="utf-8")
        else:
            file_path.write_text(content, encoding="utf-8")
        return file_path

    def build_tech_note(self, tech: str, lead_id: int) -> Path:
        file_path = self.tech_dir / f"Tech-{tech.replace('/', '_')}.md"
        content = (
            f"# Technology: {tech}\n\n"
            f"## Mentions\n"
            f"- [[Lead-{lead_id}]]\n"
        )
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
            if f"[[Lead-{lead_id}]]" not in existing:
                existing += f"- [[Lead-{lead_id}]]\n"
                file_path.write_text(existing, encoding="utf-8")
        else:
            file_path.write_text(content, encoding="utf-8")
        return file_path

    def build_pipeline_canvas(self) -> Path:
        canvas_path = self.canvases_dir / "LeadPipeline.canvas"
        nodes = []
        edges = []

        lead_files = list(self.leads_dir.glob("*.md"))
        for idx, f in enumerate(lead_files[:10]):
            nodes.append({
                "id": f"node_{idx}",
                "type": "file",
                "file": f"Leads/{f.name}",
                "x": (idx % 3) * 350,
                "y": (idx // 3) * 250,
                "width": 300,
                "height": 200,
            })

        canvas_data = {"nodes": nodes, "edges": edges}
        canvas_path.write_text(json.dumps(canvas_data, indent=2), encoding="utf-8")
        return canvas_path
