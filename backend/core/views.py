from django.http import JsonResponse


def health(_request):
    response = JsonResponse({'status': 'ok'})
    response['Cache-Control'] = 'no-store'
    return response
