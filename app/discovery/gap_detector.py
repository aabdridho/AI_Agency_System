from app.models.schemas import RequirementItem

BASE_GAPS = {
    "portfolio": [
        ("target_audience", "Siapa target utama website portfolio ini?"),
        ("visual_direction", "Gaya visual seperti apa yang paling diinginkan?"),
        ("required_sections", "Section apa saja yang wajib ada?"),
        ("contact_behavior", "Contact section cukup menampilkan kontak atau perlu form yang mengirim data?")
    ]
}

class GapDetector:
    def detect(self, project_type: str, existing_keys: set[str]):
        unknown, questions, question_map = [], [], {}
        gaps = BASE_GAPS.get(project_type, [
            ("project_goal", "Apa tujuan utama website ini?"),
            ("target_audience", "Siapa target utama website ini?"),
            ("required_features", "Fitur apa saja yang wajib tersedia?"),
            ("visual_direction", "Gaya visual seperti apa yang diinginkan?")
        ])

        for key, question in gaps:
            # Explicit required sections already define the concrete page scope.
            # Do not ask the client a second generic "required features" question.
            if (
                key == "required_features"
                and "required_sections" in existing_keys
            ):
                continue

            if key not in existing_keys:
                unknown.append(RequirementItem(
                    key=key, value=None, status="UNKNOWN",
                    source="gap_detector", blocking=True
                ))
                questions.append(question)
                question_map[key] = question

        return unknown, questions, question_map
