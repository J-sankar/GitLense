from fastapi import Header, HTTPException, status
import uuid

async def get_gateway_user(
    # FastAPI automatically converts "X-User-ID" to a variable name, 
    # but using 'alias' ensures exact matching
    x_user_id: str | None = Header(default=None, alias="X-User-ID")
) -> uuid.UUID:
    """
    Extracts the authenticated user's ID from the NGINX gateway header.
    """
    if not x_user_id:
        # If NGINX is configured correctly, this should never happen,
        # but it protects you if someone accidentally opens the container port directly.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing User ID header. Are you bypassing the gateway?"
        )
    
    try:
        # Convert the string header back into a Python UUID object for your database
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid User ID format"
        )