from django.urls import path

from . import views

app_name = 'detection'

urlpatterns = [
    path('detection/', views.list_data, name='listdata'),
    path('detection/overview', views.data_overview, name='overview'),
    path('detection/viewimages', views.view_images, name='viewimages'),
    path('image', views.show_image, name='showimage'),
]