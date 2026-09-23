import re

from app.knowledge.product_guide import (
    PRODUCT_GUIDE,
    GuideArticle,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "can",
    "do",
    "does",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "the",
    "to",
    "what",
    "where",
}


def normalize(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(value.casefold()))


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in TOKEN_PATTERN.findall(value.casefold())
        if token not in STOP_WORDS
    }


class ProductGuideService:
    @staticmethod
    def search(
        question: str,
        limit: int = 3,
    ) -> list[GuideArticle]:
        normalized_question = normalize(question)
        question_tokens = tokenize(question)

        scored: list[tuple[int, GuideArticle]] = []

        for article in PRODUCT_GUIDE:
            title_tokens = tokenize(article.title)
            content_tokens = tokenize(article.content)
            keyword_tokens = tokenize(" ".join(article.keywords))

            score = 0

            for keyword in article.keywords:
                if normalize(keyword) in normalized_question:
                    score += 10

            score += 4 * len(question_tokens & title_tokens)
            score += 2 * len(question_tokens & keyword_tokens)
            score += len(question_tokens & content_tokens)

            if score > 0:
                scored.append((score, article))

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].title,
            )
        )

        if scored:
            return [
                article
                for _, article in scored[:limit]
            ]

        return [
            article
            for article in PRODUCT_GUIDE
            if article.slug == "penflow-overview"
        ]