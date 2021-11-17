from django.urls import path

from . import views

urlpatterns = [
    path('news/', views.PostList.as_view(), name='post_list'),
    path('news/<int:pk>', views.PostContent.as_view(), name='post_detail')]
