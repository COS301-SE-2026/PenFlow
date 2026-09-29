from app.schemas.assistant import AssistantQueryRequest


def build_routing_text(
        request: AssistantQueryRequest,
) -> str:
    previous_user_message = next(
        (
            message.content
            for message in reversed(request.history)
            if message.role == "user"
        ),
        None,
    )

    if previous_user_message is None:
        return request.question

    return (
        f"{previous_user_message}\n"
        f"Follow-up: {request.question}"
    )


def build_prompt_question(
        request: AssistantQueryRequest,
) -> str:
    if not request.history:
        return request.question

    history_text = "\n".join(
        (
            f"{message.role.title()}: "
            f"{message.content}"
        )
        for message in request.history
    )

    return (
        "Recent conversation:\n"
        f"{history_text}\n\n"
        "Current user question:\n"
        f"{request.question}"
    )