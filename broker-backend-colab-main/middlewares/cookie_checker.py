from fastapi import Request, HTTPException
import os
from fastapi.routing import APIRoute
from jwt import decode as jwt_decode, ExpiredSignatureError, InvalidTokenError
from fastapi.responses import JSONResponse

# JWT Configuration
ALGORITHM = os.getenv("ALGORITHM")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

class CookieAuthRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def verify_cookie_middleware(request: Request):
            # Extract the token from cookies
            token = request.cookies.get("access_token")
            if not token:
                return JSONResponse(
                    {"detail": "No token provided"},
                    status_code=401,
                )

            # Validate the token
            try:
                payload = jwt_decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
                print(payload)
                user_id = payload.get("user_id")
                if not user_id:
                    raise HTTPException(status_code=401, detail="Invalid token")

                # Add user information to the request
                request.state.user = {"user_id": user_id}
            except ExpiredSignatureError:
                return JSONResponse(
                    {"detail": "Token expired"},
                    status_code=401,
                )
            except InvalidTokenError:
                return JSONResponse(
                    {"detail": "Invalid tokenn"},
                    status_code=401,
                )
            except Exception as e:
                return JSONResponse(
                    {"detail": f"Token validation error: {str(e)}"},
                    status_code=500,
                )

            # Proceed with the original route
            return await original_route_handler(request)

        return verify_cookie_middleware
