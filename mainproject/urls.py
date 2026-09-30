from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', lambda request: redirect('/Guest/index/')),  # Homepage

    path('Basics/', include('Basics.urls')),
    path('Admin/', include('Admin.urls')),
    path('Guest/', include('Guest.urls')),
    path('User/', include('User.urls')),
    path('Shop/', include('Shop.urls')),
    path('Doctor/', include('Doctor.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static('/Assets/', document_root=settings.BASE_DIR / 'Assets')