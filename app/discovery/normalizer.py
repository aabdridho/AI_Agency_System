import re
from app.models.schemas import RequirementItem

VISUAL_SYNONYMS = {
    "minimalist": ["minimalist", "minimal", "simple", "tidak terlalu ramai", "nggak terlalu ramai"],
    "modern": ["modern", "contemporary"],
    "clean": ["clean", "bersih"],
    "professional": ["professional", "profesional"],
    "premium": ["premium", "elegant", "eksklusif"],
}

THEME_SYNONYMS = {
    "dark": ["dark theme", "dark mode", "tema gelap", "mode gelap", "dark ui", "dark"],
    "light": ["light theme", "light mode", "tema terang", "mode terang", "light ui"],
}

SECTION_SYNONYMS = {
    "hero": ["hero", "hero section"],
    "about": [
        "about",
        "about me",
        "about us",
        "tentang saya",
        "tentang kami",
        "tentang perusahaan",
    ],
    "services": [
        "service",
        "services",
        "service section",
        "services section",
        "layanan",
        "bagian layanan",
    ],
    "skills": ["skill", "skills", "keahlian"],
    "experience": ["experience", "pengalaman"],
    "projects": ["project", "projects", "proyek"],
    "certifications": ["sertifikasi", "certification", "certifications", "certificate"],
    "contact": ["contact", "kontak", "contact form"],
    "testimonials": ["testimonial", "testimonials", "testimoni"],
}

AUDIENCE_PATTERNS = [
    # "Target utama UMKM dan startup."
    r"\btarget\s+utama(?:\s+website)?(?:\s+ini)?"
    r"\s*(?::|adalah|untuk)?\s+([^.!;\n]+)",

    # "Target website ini adalah UMKM."
    r"\btarget(?:\s+website)?(?:\s+ini)?"
    r"\s+(?:untuk|adalah)\s+([^.!;\n]+)",

    # "Audiens utama: mahasiswa."
    r"\b(?:audience|audiens|sasaran)"
    r"(?:\s+utama)?\s*(?::|adalah)?\s+([^.!;\n]+)",

    # "Ditujukan untuk pemilik UMKM."
    r"\b(?:ditujukan|diperuntukkan)\s+untuk\s+([^.!;\n]+)",

    r"untuk\s+(recruiter[^.!;\n]+)",
]

DEFAULT_CONTACT_FIELDS = ["name", "email", "message"]
STANDARD_PORTFOLIO_SECTIONS = ["hero", "about", "skills", "experience", "projects", "certifications", "contact"]

class RequirementNormalizer:
    def extract_visual_direction(self, prompt: str):
        p = prompt.lower()
        found = []
        for canonical, synonyms in VISUAL_SYNONYMS.items():
            if any(s in p for s in synonyms):
                found.append(canonical)
        return sorted(set(found))

    def extract_theme(self, prompt: str):
        p = prompt.lower()
        for canonical, synonyms in THEME_SYNONYMS.items():
            if any(re.search(rf"\b{re.escape(s)}\b", p) for s in synonyms):
                return canonical
        return None

    def extract_sections(self, prompt: str):
        return self.normalize_sections(prompt)

    def normalize_sections(self, text: str):
        p = text.lower()
        found = []
        for canonical, synonyms in SECTION_SYNONYMS.items():
            if any(re.search(rf"\b{re.escape(s)}\b", p) for s in synonyms):
                found.append(canonical)
        return sorted(set(found))

    def extract_target_audience(self, prompt: str):
        for pattern in AUDIENCE_PATTERNS:
            m = re.search(pattern, prompt, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip(" .")

        p = prompt.lower()
        known = []
        if "recruiter" in p or re.search(r"\bhr\b", p):
            known.append("recruiter / HR")
        if "perusahaan teknologi" in p or "tech company" in p:
            known.append("perusahaan teknologi")
        if "calon client" in p or "calon klien" in p:
            known.append("calon client")
        return ", ".join(dict.fromkeys(known)) if known else None

    def extract_project_goal(self, prompt: str):
        p = prompt.lower()
        goals = []

        job_patterns = [
            "cari kerja",
            "mencari kerja",
            "melamar kerja",
            "job hunting",
            "job search",
            "recruiter",
            "hr",
        ]
        client_patterns = [
            "cari client",
            "cari klien",
            "mendapatkan calon client",
            "mendapatkan client",
            "mendapatkan klien",
            "calon client",
            "calon klien",
            "menawarkan jasa",
            "membutuhkan jasa",
        ]

        if any(x in p for x in job_patterns):
            goals.append("job_search")
        if any(x in p for x in client_patterns):
            goals.append("client_acquisition")

        if not goals:
            return None
        if len(goals) == 1:
            return goals[0]
        return goals

    def normalize_contact_behavior(self, text: str):
        p = text.lower().strip()

        display_only_patterns = [
            r"\bhanya\s+(?:menampilkan|tampilkan)\s+kontak\b",
            r"\bhanya\s+menampilkan\s+email\b",
            r"\btampilkan\s+kontak\b",
            r"\bkontak\s+saja\b",
            r"\bhanya\s+kontak\b",
            r"\bdisplay\s+only\b",
            r"\btanpa\s+form\b",
            r"\btidak\s+perlu\s+form\b",
            r"\btak\s+perlu\s+form\b",
            r"\bnggak\s+perlu\s+form\b",
            r"\bgak\s+perlu\s+form\b",
            r"\bno\s+form\b",
            r"\bwithout\s+(?:a\s+)?form\b",
        ]
        if any(re.search(pattern, p) for pattern in display_only_patterns):
            return "display_only"

        form_patterns = [
            r"\bform\b",
            r"\bmengisi(?:kan)?\s+data\b",
            r"\bisi\s+data\b",
            r"\binput\s+data\b",
            r"\bmengirim(?:kan)?\s+data\b",
            r"\bkirim(?:kan)?\s+data\b",
            r"\bsubmit\b",
            r"\bpengunjung\s+(?:bisa|dapat)\s+mengisi\b",
        ]
        if any(re.search(pattern, p) for pattern in form_patterns):
            return "contact_form"

        # Bare/ambiguous answers such as "kontak" or "contact"
        # are intentionally not accepted as an implementation requirement.
        ambiguous = {
            "kontak",
            "contact",
            "contact section",
            "bagian kontak",
            "ya",
            "iya",
            "yes",
        }
        if p in ambiguous:
            return None

        # Unknown phrasing should also be clarified rather than silently accepted.
        return None

    def normalize_contact_destination(self, text: str):
        p = text.lower().strip()
        if "email" in p:
            return "email"
        if "whatsapp" in p or re.search(r"\bwa\b", p):
            return "whatsapp"
        if "database" in p or re.search(r"\bdb\b", p):
            return "database"
        if "crm" in p:
            return "crm"
        if "webhook" in p:
            return "webhook"
        return text.strip()

    def normalize_contact_fields(self, text: str):
        p = text.lower().strip()

        if any(x in p for x in [
            "sesuai contoh",
            "sesuai saran",
            "yang dicontohkan",
            "contoh aja",
            "contoh",
            "pakai contoh",
            "yang tadi",
            "itu aja",
            "seperti contoh",
        ]):
            return list(DEFAULT_CONTACT_FIELDS)

        aliases = {
            "name": ["nama", "name"],
            "email": ["email", "e-mail"],
            "phone": ["nomor", "no hp", "no. hp", "telepon", "phone", "whatsapp", "wa"],
            "company": ["company", "perusahaan"],
            "subject": ["subject", "subjek"],
            "message": ["pesan", "message"],
        }

        result = []
        for canonical, synonyms in aliases.items():
            if any(re.search(rf"\b{re.escape(s)}\b", p) for s in synonyms):
                result.append(canonical)

        return result if result else [x.strip() for x in text.split(",") if x.strip()]

    def is_all_sections_answer(self, text: str):
        p = text.lower().strip()
        return p in {
            "semua",
            "all",
            "semuanya",
            "semua section",
            "semua bagian",
            "pakai semua",
        }

    def standard_portfolio_sections(self):
        return list(STANDARD_PORTFOLIO_SECTIONS)

    def extract_contact_details(self, prompt: str):
        p = prompt.lower()
        items = []

        behavior = self.normalize_contact_behavior(prompt)

        if behavior:
            items.append(RequirementItem(
                key="contact_behavior",
                value=behavior,
                status="CONFIRMED",
                source="client_prompt_normalized",
                blocking=False,
                confidence=1.0,
            ))

        if (
            behavior == "display_only"
            and "email" in p
        ):
            items.append(RequirementItem(
                key="contact_destination",
                value="email",
                status="CONFIRMED",
                source="client_prompt_normalized",
                blocking=False,
                confidence=1.0,
            ))

        if "contact form" in p or re.search(r"\bform\s+kontak\b", p):
            items.append(RequirementItem(
                key="contact_behavior", value="contact_form",
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=1.0
            ))

        if re.search(r"(?:contact form|form kontak)[^.]{0,80}\bemail\b", p) or \
           re.search(r"\bkirim(?:kan)?\s+ke\s+email\b", p):
            items.append(RequirementItem(
                key="contact_destination", value="email",
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=1.0
            ))

        field_match = re.search(
            r"field\s+wajib\s+([^.!]+)",
            prompt,
            flags=re.IGNORECASE
        )
        if field_match:
            fields = self.normalize_contact_fields(field_match.group(1))
            if fields:
                items.append(RequirementItem(
                    key="contact_fields", value=fields,
                    status="CONFIRMED", source="client_prompt_normalized",
                    blocking=False, confidence=1.0
                ))

        return items

    def extract_prompt_confirmed(self, prompt: str):
        items = []

        visual = self.extract_visual_direction(prompt)
        if visual:
            items.append(RequirementItem(
                key="visual_direction", value=visual,
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=1.0
            ))

        theme = self.extract_theme(prompt)
        if theme:
            items.append(RequirementItem(
                key="theme", value=theme,
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=1.0
            ))

        sections = self.extract_sections(prompt)
        if sections:
            items.append(RequirementItem(
                key="required_sections", value=sections,
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=1.0
            ))

        audience = self.extract_target_audience(prompt)
        if audience:
            items.append(RequirementItem(
                key="target_audience", value=audience,
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=0.95
            ))

        goal = self.extract_project_goal(prompt)
        if goal:
            items.append(RequirementItem(
                key="project_goal", value=goal,
                status="CONFIRMED", source="client_prompt_normalized",
                blocking=False, confidence=1.0
            ))

        items.extend(self.extract_contact_details(prompt))
        return items
