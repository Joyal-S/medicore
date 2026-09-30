from django.urls import path,include
from Guest import views
app_name="Guest"
urlpatterns = [
    path('login/',views.login,name='login'),
    path('registration/',views.registration,name='registration'),
    path('ajaxplace/',views.ajaxplace,name='ajaxplace'),
    path('doctor/',views.doctor,name='doctor'),
    path('shop/',views.shop,name='shop'),
    path('index/',views.index,name='index'),
   
]