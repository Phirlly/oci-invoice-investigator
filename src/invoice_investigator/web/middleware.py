class ResponsePolicy:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; "
                "style-src 'self'; img-src 'self' data:; font-src 'self'; "
                "connect-src 'self'; worker-src 'self'; frame-ancestors 'none'; "
                "object-src 'none'; base-uri 'none'; form-action 'self'"
            ),
        )
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
