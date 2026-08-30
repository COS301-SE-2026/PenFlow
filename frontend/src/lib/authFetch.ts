export async function authenticatedFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
): Promise<Response> {
    const response = await fetch(input, init);

    if(response.status !== 401) {
        return response;
    }

    try {
        const retryResponse = await navigator.locks.request(
            "penflow-auth-refresh",
            async () => {
                const retryAfterWait = await fetch(input, init);

                if(retryAfterWait.status !== 401) {
                    return retryAfterWait;
                }

                const refreshResponse = await fetch("/api/auth/refresh", {method: "POST"});

                if(!refreshResponse.ok) {
                    return null;
                }

                return fetch(input, init);
            }
        );

        if(retryResponse === null) {
            window.location.href = "/api/auth/logout";
            return response;
        }

        if(retryResponse.status === 401) {
            window.location.href = "/api/auth/logout";
        }

        return retryResponse;
    } catch {
        window.location.href = "/api/auth/logout";
        return response;
    }
}