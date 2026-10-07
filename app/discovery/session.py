from app.discovery.confirmation import ConfirmationGate
from app.discovery.gap_detector import GapDetector
from app.discovery.normalizer import RequirementNormalizer
from app.discovery.dependency_expander import DependencyExpander
from app.discovery.deduplicator import SemanticDeduplicator
from app.models.schemas import DiscoveryResult

YES = {"y", "yes", "iya", "ya"}

class InteractiveConfirmationSession:
    def __init__(self):
        self.gate = ConfirmationGate()
        self.gap_detector = GapDetector()
        self.normalizer = RequirementNormalizer()
        self.expander = DependencyExpander()
        self.deduplicator = SemanticDeduplicator()

    def run(self, result: DiscoveryResult) -> DiscoveryResult:
        print("\n=== CLIENT CONFIRMATION ===")

        for item in list(result.inferred):
            print("\nDari referensi, sistem menemukan kemungkinan requirement:")
            print(f"- {item.key}: {item.value}")
            ans = input("Apakah ini sesuai keinginan client? [y/n]: ").strip().lower()
            if ans in YES:
                value = input(
                    f"Konfirmasi nilai '{item.key}' (Enter untuk memakai '{item.value}'):\n> "
                ).strip()
                cleaned_value = value.strip().strip("\\")
                result = self.gate.promote_confirmed(
                    result, item.key, cleaned_value if cleaned_value else item.value
                )
            else:
                result = result.model_copy(update={
                    "inferred": [x for x in result.inferred if x.key != item.key]
                })

        _, _, question_map = self.gap_detector.detect(
            result.project_type, {x.key for x in result.confirmed}
        )

        for item in list(result.unknown):
            question = question_map.get(item.key, f"Berikan nilai untuk {item.key}:")
            print(f"\n{question}")
            answer = input("> ").strip()
            while not answer:
                print("Jawaban diperlukan karena requirement ini bersifat blocking.")
                answer = input("> ").strip()

            if item.key == "contact_behavior":
                normalized = self.normalizer.normalize_contact_behavior(answer)
                while normalized is None:
                    print("\nJawaban masih ambigu.")
                    print("Pilih salah satu:")
                    print("1. Hanya menampilkan informasi kontak")
                    print("2. Menggunakan form yang dapat mengirim data")
                    answer = input("> ").strip()

                    if answer == "1":
                        normalized = "display_only"
                    elif answer == "2":
                        normalized = "contact_form"
                    else:
                        normalized = self.normalizer.normalize_contact_behavior(answer)

                answer = normalized

            elif item.key == "required_sections":
                if self.normalizer.is_all_sections_answer(answer):
                    suggested = self.normalizer.standard_portfolio_sections()
                    print("\n' Semua ' masih ambigu untuk kebutuhan audit.")
                    print("Apakah yang dimaksud semua section standar berikut?")
                    print(", ".join(suggested))
                    confirm_all = input("Gunakan semua section tersebut? [y/n]: ").strip().lower()

                    if confirm_all in YES:
                        answer = suggested
                    else:
                        print("Sebutkan section yang benar-benar diinginkan.")
                        answer = input("> ").strip()
                        while not answer:
                            print("Jawaban diperlukan.")
                            answer = input("> ").strip()
                        normalized_sections = self.normalizer.normalize_sections(answer)
                        answer = normalized_sections if normalized_sections else answer
                else:
                    normalized_sections = self.normalizer.normalize_sections(answer)
                    answer = normalized_sections if normalized_sections else answer

            elif item.key == "visual_direction":
                normalized_visual = self.normalizer.extract_visual_direction(answer)
                answer = normalized_visual if normalized_visual else answer

            elif item.key == "reference_preferences":
                prefs = []
                p = answer.lower()
                for canonical, words in {
                    "layout": ["layout"],
                    "animation": ["animasi", "animation"],
                    "typography": ["typography", "tipografi"],
                    "color": ["warna", "color"],
                    "spacing": ["spacing"],
                }.items():
                    if any(w in p for w in words):
                        prefs.append(canonical)
                answer = sorted(set(prefs)) if prefs else answer

            result = self.gate.promote_confirmed(result, item.key, answer)

        # Expand dependent requirements after core answers are known.
        dependent_unknowns = self.expander.expand(result.confirmed)

        for item in dependent_unknowns:
            if item.key == "contact_destination":
                print("\nContact form akan mengirim data ke mana?")
                print("Contoh: email, WhatsApp, database, CRM, webhook")
                answer = input("> ").strip()
                while not answer:
                    print("Jawaban diperlukan.")
                    answer = input("> ").strip()
                answer = self.normalizer.normalize_contact_destination(answer)

            elif item.key == "contact_fields":
                print("\nField apa saja yang wajib diisi pada contact form?")
                print("Contoh: nama, email, pesan")
                answer = input("> ").strip()
                while not answer:
                    print("Jawaban diperlukan.")
                    answer = input("> ").strip()
                answer = self.normalizer.normalize_contact_fields(answer)
            else:
                answer = input(f"\nBerikan nilai untuk {item.key}:\n> ").strip()

            result = self.gate.promote_confirmed(result, item.key, answer)

        for item in list(result.proposed):
            print(f"\nSaran tambahan: {item.value}")
            ans = input("Tambahkan ke requirement? [y/n]: ").strip().lower()

            if ans in YES and item.key.startswith("section_"):
                section_name = item.key.replace("section_", "", 1)

                required = next(
                    (x for x in result.confirmed if x.key == "required_sections"),
                    None
                )
                current = []
                if required and isinstance(required.value, list):
                    current = list(required.value)

                current = sorted(set(current + [section_name]))
                result = self.gate.promote_confirmed(
                    result,
                    "required_sections",
                    current,
                    source="client_approved_proposal"
                )
                result = result.model_copy(update={
                    "proposed": [x for x in result.proposed if x.key != item.key]
                })

            elif ans in YES:
                result = self.gate.promote_confirmed(
                    result, item.key, item.value, source="client_approved_proposal"
                )
            else:
                result = result.model_copy(update={
                    "proposed": [x for x in result.proposed if x.key != item.key]
                })

        cleaned = self.deduplicator.clean_confirmed(result.confirmed)

        result = result.model_copy(update={
            "confirmed": cleaned,
            "questions": [],
            "ready_for_final_approval": self.gate.can_final_approve(result),
            "ready_for_development": False,
            "client_approved": False
        })
        return result
