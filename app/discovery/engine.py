from app.discovery.extractor import RequirementExtractor
from app.discovery.normalizer import RequirementNormalizer
from app.discovery.reference_analyzer import ReferenceAnalyzer
from app.discovery.gap_detector import GapDetector
from app.discovery.question_generator import QuestionGenerator
from app.discovery.confirmation import ConfirmationGate
from app.discovery.proposal_engine import ProposalEngine
from app.discovery.deduplicator import SemanticDeduplicator
from app.models.schemas import RequirementItem, DiscoveryResult

def merge_items(items):
    merged = {}
    for item in items:
        merged[item.key] = item
    return list(merged.values())

class RequirementDiscoveryEngine:
    def __init__(self):
        self.extractor = RequirementExtractor()
        self.normalizer = RequirementNormalizer()
        self.reference_analyzer = ReferenceAnalyzer()
        self.gap_detector = GapDetector()
        self.question_generator = QuestionGenerator()
        self.confirmation_gate = ConfirmationGate()
        self.proposal_engine = ProposalEngine()
        self.deduplicator = SemanticDeduplicator()

    def analyze(self, prompt: str, references: list[str] | None = None) -> DiscoveryResult:
        references = references or []
        project_type = self.extractor.detect_project_type(prompt)

        confirmed = merge_items(
            self.extractor.extract_confirmed(prompt)
            + self.normalizer.extract_prompt_confirmed(prompt)
        )
        confirmed = self.deduplicator.clean_confirmed(confirmed)

        ref_confirmed, inferred, ref_unknown = self.reference_analyzer.analyze(prompt, references)
        confirmed = merge_items(confirmed + ref_confirmed)

        existing_keys = {x.key for x in confirmed} | {x.key for x in inferred}
        unknown, questions, _ = self.gap_detector.detect(project_type, existing_keys)
        unknown.extend(ref_unknown)

        if any(x.key == "reference_preferences" for x in ref_unknown):
            questions.append(
                "Dari website referensi yang diberikan, bagian apa yang paling ingin dijadikan acuan? "
                "Contoh: layout, animasi, typography, warna."
            )

        internal_decisions = [
            RequirementItem(
                key="discovery_engine_version", value="0.3-stable",
                status="INTERNAL_DECISION", source="system",
                blocking=False, confidence=1.0
            )
        ]
        if "deployment_target" not in existing_keys:
            internal_decisions.append(RequirementItem(
                key="deployment_target", value="to_be_decided_internally",
                status="INTERNAL_DECISION", source="system_policy",
                blocking=False, confidence=1.0
            ))

        confirmed_sections = set()
        for item in confirmed:
            if item.key == "required_sections" and isinstance(item.value, list):
                confirmed_sections.update(item.value)

        proposed = self.proposal_engine.build(
            project_type,
            {x.key for x in confirmed},
            confirmed_sections,
            prompt
        )

        result = DiscoveryResult(
            project_type=project_type,
            confirmed=confirmed,
            inferred=inferred,
            proposed=proposed,
            unknown=unknown,
            internal_decisions=internal_decisions,
            questions=self.question_generator.limit_questions(questions),
            ready_for_final_approval=False,
            client_approved=False,
            ready_for_development=False
        )

        return result.model_copy(update={
            "ready_for_final_approval": self.confirmation_gate.can_final_approve(result)
        })
