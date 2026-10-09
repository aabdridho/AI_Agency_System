class QuestionGenerator:
    def limit_questions(
        self,
        questions: list[str],
        max_questions: int = 5,
    ) -> list[str]:
        return questions[:max_questions]

    def contextualize(
        self,
        project_type: str,
        unknown,
        confirmed,
        fallback_questions: list[str],
    ) -> list[str]:
        confirmed_values = {
            item.key: item.value
            for item in confirmed
        }

        fallback_by_key = {
            item.key: question
            for item, question in zip(
                unknown,
                fallback_questions,
            )
        }

        result = []

        for item in unknown:
            key = item.key

            if (
                key == "project_goal"
                and project_type == "landing_page"
            ):
                audience = confirmed_values.get(
                    "target_audience"
                )

                if audience:
                    result.append(
                        "Setelah target audience "
                        f"{audience} melihat landing page ini, "
                        "aksi utama apa yang ingin diarahkan: "
                        "WhatsApp, form konsultasi, email, "
                        "atau booking meeting?"
                    )
                else:
                    result.append(
                        "Aksi utama apa yang ingin dilakukan "
                        "pengunjung setelah melihat landing page: "
                        "WhatsApp, form konsultasi, email, "
                        "atau booking meeting?"
                    )
                continue

            if key == "target_audience":
                result.append(
                    "Siapa pengguna atau calon klien utama "
                    "yang ingin dijangkau project ini?"
                )
                continue

            if key == "visual_direction":
                result.append(
                    "Arah visual apa yang belum disebutkan "
                    "dan perlu ditetapkan, misalnya minimalis, "
                    "corporate, playful, premium, atau lainnya?"
                )
                continue

            question = fallback_by_key.get(key)

            if question:
                result.append(question)

        return self.limit_questions(result)
