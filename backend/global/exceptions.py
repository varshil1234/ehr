from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data

        # Handle ValidationError with non_field_errors
        if isinstance(exc, ValidationError):
            if isinstance(detail, dict) and "non_field_errors" in detail:
                detail = detail["non_field_errors"][0]
        
        if isinstance(detail, dict) and "detail" in detail:
                detail = detail["detail"]

        response.data = {
            "status": "error",
            "detail": detail
        }

    return response
