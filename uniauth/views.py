from django.shortcuts import render

def index(request):
    return render(request, 'uniauth/index.html')
