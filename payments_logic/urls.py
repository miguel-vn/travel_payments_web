from django.urls import path

from . import views

urlpatterns = [
    path('', views.TravelsList.as_view(), name='travels_list'),
    path('about', views.about_page, name='about'),
    path('new_travel', views.CreateTravel.as_view(), name='new_travel'),
    path('new_person', views.NewPerson.as_view(), name='new_person'),
    path('travel_detail/<int:pk>/', views.TravelDetail.as_view(), name='travel_detail'),
    path('travel_detail/<int:pk>/delete', views.DeleteTravel.as_view(), name='travel_delete'),
    path('travel_detail/<int:pk>/update', views.UpdateTravel.as_view(), name='travel_update'),
    path('travel_detail/<int:travel_pk>/new_payment', views.AddPayment.as_view(), name='new_payment'),
    path('travel_detail/<int:pk>/summary', views.SummaryPaymentsAndDebts.as_view(), name='summaries'),
]
