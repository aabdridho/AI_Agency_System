class QuestionGenerator:
    def limit_questions(self, questions: list[str], max_questions: int = 5) -> list[str]:
        return questions[:max_questions]
