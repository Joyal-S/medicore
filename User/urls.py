from django.urls import path,include
from User import views
app_name="User"
urlpatterns = [
    path('home/',views.home,name='home'),  
    path('myprofile/',views.myprofile,name='myprofile'),
    path('editprofile/',views.editprofile,name='editprofile'),
    path('changepass/',views.changepass,name='changepass'), 
    path('complaints/',views.complaints,name='complaints'),
    path('viewdoctor/',views.viewdoctor,name='viewdoctor'),
    path('request/<int:id>',views.request,name='request'),
    path('viewrequest/',views.viewrequest,name='viewrequest'),
    path('viewprescription/<int:id>',views.viewprescription,name='viewprescription'),
    path('viewshop/',views.viewshop,name='viewshop'),
    path('viewmedicine/<int:id>',views.viewmedicine,name='viewmedicine'),
    path('Addcart/<int:mid>',views.Addcart, name='Addcart'),  
    path('Mycart/',views.Mycart, name='Mycart'), 
    path("DelCart/<int:did>", views.DelCart,name="delcart"),
    path("CartQty/", views.CartQty,name="cartqty"),
    path('payment/<int:id>',views.payment, name='payment'), 
    path('payment_suc/',views.payment_suc, name='payment_suc'), 
    path('addprescription/<int:id>',views.addprescription, name='addprescription'),
    path('search/',views.search, name='search'), 
    path('myorder/',views.myorder, name='myorder'),
    path('rating/<int:mid>',views.rating,name="rating"),  
    path('ajaxstar/',views.ajaxstar,name="ajaxstar"),
    path('starrating/',views.starrating,name="starrating"),
    path('ulogout/',views.ulogout, name='ulogout')

    
]