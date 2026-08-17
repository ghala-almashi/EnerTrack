from django.urls import path
from . import views  

urlpatterns = [

    path( '', views.dashboard_view, name='dashboard_home'), 
    path('device/<str:device_id>/', views.device_detail_view, name='device_detail'),
]
