import re
from app.models.schemas import RequirementItem

PROJECT_KEYWORDS = {
    "portfolio": ["portfolio", "portofolio"],
    "company_profile": ["company profile", "profil perusahaan"],
    "ecommerce": ["ecommerce", "e-commerce", "toko online"],
    "landing_page": ["landing page"],
    "blog": ["blog"],
    "dashboard": ["dashboard"],
}

FEATURE_KEYWORDS = {
    "contact": ["contact", "kontak", "contact form"],
    "portfolio_projects": ["project", "projects", "proyek"],
    "authentication": ["login", "auth", "authentication", "register"],
    "admin_dashboard": ["admin dashboard", "dashboard admin"],
    "cms": ["cms", "content management"],
    "database": ["database", "db"],
    "responsive": ["responsive", "mobile friendly", "mobile-first"],
}

FOCUS_PATTERNS = [
    r"portfolio\s+(?:untuk|for)\s+([A-Za-z][A-Za-z\s&+\-/]{2,60})",
    r"portofolio\s+(?:untuk|for)\s+([A-Za-z][A-Za-z\s&+\-/]{2,60})",
    r"portfolio\s+(Data\s+Engineer(?:ing)?)",
    r"portofolio\s+(Data\s+Engineer(?:ing)?)",
    r"portfolio(?:\s+[A-Za-z]+){0,4}\s+(?:untuk|for)\s+(Data\s+Engineer(?:ing)?)",
    r"portofolio(?:\s+[A-Za-z]+){0,4}\s+(?:untuk|for)\s+(Data\s+Engineer(?:ing)?)",
]

DEPLOYMENT_KEYWORDS = {
    "vercel": ["vercel"],
    "hostinger": ["hostinger"],
    "netlify": ["netlify"],
    "cloudflare_pages": ["cloudflare pages"],
}

class RequirementExtractor:
    def detect_project_type(self, prompt: str) -> str:
        p = prompt.lower()
        for project_type, keywords in PROJECT_KEYWORDS.items():
            if any(k in p for k in keywords):
                return project_type
        return "unknown"

    def extract_confirmed(self, prompt: str) -> list[RequirementItem]:
        p = prompt.lower()
        items = []

        for key, keywords in FEATURE_KEYWORDS.items():
            if any(k in p for k in keywords):
                items.append(RequirementItem(
                    key=key, value=True, status="CONFIRMED",
                    source="client_prompt", blocking=False, confidence=1.0
                ))

        for pattern in FOCUS_PATTERNS:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                raw = match.group(1)
                raw = re.split(
                    r"\b(?:dengan|yang|dan\s+ada|memiliki|berisi|menggunakan)\b",
                    raw, maxsplit=1, flags=re.IGNORECASE
                )[0].strip(" .,-")
                if raw:
                    items.append(RequirementItem(
                        key="portfolio_focus", value=raw,
                        status="CONFIRMED", source="client_prompt",
                        blocking=False, confidence=1.0
                    ))
                break

        for provider, keywords in DEPLOYMENT_KEYWORDS.items():
            if any(k in p for k in keywords):
                items.append(RequirementItem(
                    key="deployment_target", value=provider,
                    status="CONFIRMED", source="client_prompt",
                    blocking=False, confidence=1.0
                ))
                break

        return items
