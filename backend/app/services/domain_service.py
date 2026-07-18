from fastapi import HTTPException, status

class DomainService:

    @staticmethod
    def strip_domain(domain: str) -> str:
        stripped = domain.strip().lower()
        
        if stripped.startswith("https://"):
            stripped = stripped.removeprefix("https://")

        elif stripped.startswith("http://"):
            stripped = stripped.removeprefix("http://")

        stripped = stripped.split("/", maxsplit=1)[0]
        stripped = stripped.rstrip(".")

        if not stripped:
            raise HTTPException(
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail = "A valid domain is needed",
            )
        
        return stripped
    
