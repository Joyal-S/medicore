from django.urls import path,include
from Shop import views
app_name="Shop"
urlpatterns = [
    path('home/',views.home,name='home'),  
    path('myprofile/',views.myprofile,name='myprofile'),
    path('editprofile/',views.editprofile,name='editprofile'),
    path('changepass/',views.changepass,name='changepass'),
    path('category/',views.category,name='category'),
    path('medicine/',views.medicine,name='medicine'),
    path('deletemed/<int:deletemed>/',views.deletemed,name='deletemed'),
    path('addstock/<int:mid>/',views.addstock,name='addstock'),
    path('booking/',views.booking,name='booking'),
    path('delivery/<int:id>',views.delivery,name='delivery'),
    path('packing/<int:id>',views.packing,name='packing'),
    path('slogout/',views.slogout,name='slogout'),
    
]