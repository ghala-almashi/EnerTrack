from django.contrib import admin
from .models import (
    Household, Device, DeviceReading, ModelRegistry,
    AnomalyDetection, Alert, MaintenanceRecommendation, Forecast
)

admin.site.register(Household)
admin.site.register(Device)
admin.site.register(DeviceReading)
admin.site.register(ModelRegistry)
admin.site.register(AnomalyDetection)
admin.site.register(Alert)
admin.site.register(MaintenanceRecommendation)
admin.site.register(Forecast)