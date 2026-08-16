from django.db import models

class Household(models.Model):
    household_id = models.AutoField(primary_key=True)
    region = models.CharField(max_length=100)
    customer_category = models.CharField(max_length=50, blank=True)


class ModelRegistry(models.Model):
    model_version = models.CharField(max_length=50, primary_key=True)
    model_type = models.CharField(max_length=50)
    trained_at = models.DateTimeField(auto_now_add=True)


class Device(models.Model):
    device_id = models.CharField(max_length=50, primary_key=True)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="devices")
    device_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    rated_power = models.FloatField()


class DeviceReading(models.Model):
    reading_id = models.BigAutoField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="readings")
    timestamp = models.DateTimeField()
    power_kw = models.FloatField()
    voltage = models.FloatField()
    temperature = models.FloatField()
    efficiency_ratio = models.FloatField(null=True)


class AnomalyDetection(models.Model):
    detection_id = models.BigAutoField(primary_key=True)
    reading = models.OneToOneField(DeviceReading, on_delete=models.CASCADE)
    model_version = models.ForeignKey(ModelRegistry, on_delete=models.SET_NULL, null=True)
    composite_score = models.FloatField()
    severity = models.CharField(max_length=20)


class Alert(models.Model):
    STATUS_CHOICES = [("open", "مفتوح"), ("in_progress", "تحت المعالجة"), ("closed", "مغلق")]
    alert_id = models.BigAutoField(primary_key=True)
    detection = models.ForeignKey(AnomalyDetection, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class MaintenanceRecommendation(models.Model):
    rec_id = models.BigAutoField(primary_key=True)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE)
    action = models.TextField()
    due_date = models.DateField()
    completed = models.BooleanField(default=False)


class Forecast(models.Model):
    forecast_id = models.BigAutoField(primary_key=True)
    target_date = models.DateField()
    model_version = models.ForeignKey(ModelRegistry, on_delete=models.SET_NULL, null=True)
    p10 = models.FloatField()
    p50 = models.FloatField()
    p90 = models.FloatField()
    actual_value = models.FloatField(null=True, blank=True)
