"""
Custom DRF exception handler.
All API errors return a consistent JSON shape:
{
    "error": true,
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    # Call DRF's default handler first to get the standard error response
    response = exception_handler(exc, context)

    if response is not None:
        error_code = 'ERROR'
        message = 'An error occurred.'
        details = {}

        # Extract useful info from the original response data
        if isinstance(response.data, dict):
            # DRF validation errors have field-level details
            if 'detail' in response.data:
                message = str(response.data['detail'])
                # Use DRF's built-in error codes when available
                if hasattr(response.data['detail'], 'code'):
                    error_code = response.data['detail'].code.upper()
            else:
                message = 'Validation failed.'
                details = response.data
        elif isinstance(response.data, list):
            message = str(response.data[0]) if response.data else 'Error.'

        # Map HTTP status to meaningful code
        status_code_map = {
            400: 'BAD_REQUEST',
            401: 'UNAUTHORIZED',
            403: 'PERMISSION_DENIED',
            404: 'NOT_FOUND',
            405: 'METHOD_NOT_ALLOWED',
            429: 'THROTTLED',
            500: 'SERVER_ERROR',
        }

        if error_code == 'ERROR':
            error_code = status_code_map.get(response.status_code, 'ERROR')

        response.data = {
            'error': True,
            'code': error_code,
            'message': message,
            'details': details,
        }

    return response
