from django.urls import path
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from . import views

app_name = 'med_api'

@api_view(['GET'])
def api_root(request, format=None):
    """API root endpoint showing all available endpoints."""
    return Response({
        'medicines': reverse('med_api:medicine-list', request=request, format=format),
        'generics': reverse('med_api:generic-list', request=request, format=format),
        'manufacturers': reverse('med_api:manufacturer-list', request=request, format=format),
        'drug_classes': reverse('med_api:drug-class-list', request=request, format=format),
        'dosage_forms': reverse('med_api:dosage-form-list', request=request, format=format),
        'indications': reverse('med_api:indication-list', request=request, format=format),
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('medicines/', views.MedicineListView.as_view(), name='medicine-list'),
    path('medicines/<pk>/', views.MedicineDetailView.as_view(), name='medicine-detail'),
    path('drug_classes/', views.DrugClassListView.as_view(), name='drug-class-list'),
    path('drug_classes/<pk>/', views.DrugClassDetailView.as_view(), name='drug-class-detail'),
    path('generics/', views.GenericListView.as_view(), name='generic-list'),
    path('generics/<pk>/', views.GenericDetailView.as_view(), name='generic-detail'),
    path('dosage_forms/', views.DosageFormListView.as_view(), name='dosage-form-list'),
    path('dosage_forms/<pk>/', views.DosageFormDetailView.as_view(), name='dosage-form-detail'),
    path('manufacturers/', views.ManufacturerListView.as_view(), name='manufacturer-list'),
    path('manufacturers/<pk>/', views.ManufacturerDetailView.as_view(), name='manufacturer-detail'),
    path('indications/', views.IndicationListView.as_view(), name='indication-list'),
    path('indications/<pk>/', views.IndicationDetailView.as_view(), name='indication-detail'),

]
