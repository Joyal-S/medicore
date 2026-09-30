from django.urls import path,include
from Basics import views

urlpatterns = [
    path('add/',views.add,name='add'),
     path('largest/',views.largest,name='largest'),
    path('RankList/', views.RankList, name='RankList'),
     path('Amstrong/', views.amstrong, name='amstrong'),
]
