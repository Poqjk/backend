from fastapi import Request, HTTPException
from fastapi.routing import APIRoute
from utils import validate_token


class VerifyTokenRoute(APIRoute):
    def get_route_handler(self):
        original_route = super().get_route_handler()

        async def verify_token_middleware(request: Request):
            try:
                # Retrieve the Authorization header
                auth_header = request.headers.get("Authorization")
                if not auth_header:
                    raise HTTPException(status_code=401, detail="Authorization header missing")

                # Extract the token from the Authorization header
                parts = auth_header.split(" ")
                if len(parts) != 2 or parts[0] != "Bearer":
                    raise HTTPException(status_code=401, detail="Invalid Authorization header format")

                token = parts[1]
                if not token:
                    raise HTTPException(status_code=401, detail="Token missing in Authorization header")

                # Validate the token
                validation_response = validate_token(token, output=False)

                if validation_response is None:
                    # Token is valid, proceed to the original route handler
                    return await original_route(request)
                else:
                    # Token validation failed, return a 401 Unauthorized error
                    raise HTTPException(status_code=401, detail=f"Token validation failed: {validation_response}")
            except HTTPException as http_exc:
                # Propagate known HTTP exceptions as they are
                raise http_exc
            except IndexError:
                # Handle malformed Authorization header
                raise HTTPException(status_code=401, detail="Malformed Authorization header")
            except Exception as e:
                # Catch unexpected errors and return a generic 500 Internal Server Error
                raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}") from e

        return verify_token_middleware
