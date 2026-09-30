from django.urls import path,include
from Doctor import views
app_name="Doctor"
urlpatterns = [
       path('home/',views.home,name='home'),  
    path('myprofile/',views.myprofile,name='myprofile'),
    path('editprofile/',views.editprofile,name='editprofile'),
    path('changepass/',views.changepass,name='changepass'),
    path('viewrequest/',views.viewrequest,name='viewrequest'),
    path('prescription/<int:id>/',views.prescription,name='prescription'),
    path('checkdisease/<int:id>/',views.checkdisease,name='checkdisease'),
    path('dlogout/',views.dlogout,name='dlogout'),
]

