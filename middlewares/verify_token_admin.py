from fastapi import Request, HTTPException
from fastapi.routing import APIRoute
from utils import validate_token


class VerifyTokenAdmin(APIRoute):
    def get_route_handler(self):
        original_route = super().get_route_handler()

        async def verify_token_middleware(request: Request):
            try:
                # Get the Authorization header
                auth_header = request.headers.get("Authorization")
                if not auth_header:
                    raise HTTPException(status_code=401, detail="Authorization header missing")

                # Extract the token
                parts = auth_header.split(" ")
                if len(parts) != 2 or parts[0] != "Bearer":
                    raise HTTPException(status_code=401, detail="Invalid Authorization header format")

                token = parts[1]
                if not token:
                    raise HTTPException(status_code=401, detail="Token missing in Authorization header")

                # Validate the token and extract its payload
                validation_response = validate_token(token, output=True)

                # Check the role in the token payload
                
                
                if "rol" not in validation_response:
                    raise HTTPException(
                        status_code=403,
                        detail="Access denied: 'rol' is missing in the response"
                    )

                if validation_response["rol"] != "admin":
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied: Required role 'admin', but got '{validation_response['rol']}'"
                    )

                # Token is valid, proceed to the original route handler
                return await original_route(request)

            except HTTPException as http_exc:
                # Re-raise HTTP exceptions with their original status code and message
                raise http_exc
            except KeyError as e:
                # Handle missing expected fields in the token
                raise HTTPException(status_code=400, detail=f"Malformed token payload: {str(e)}")
            except Exception as e:
                # Catch unexpected errors and return a generic error response
                raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}") from e

        return verify_token_middleware
