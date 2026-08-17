from django.shortcuts import render
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta
from .models import Forecast
import random

from .models import Device, Alert, DeviceReading


def dashboard_view(request):
    # اجمالي التنبيهات
    all_alerts = Alert.objects.all()
    total_alerts_count = all_alerts.count()

    #ملخص الاجهزه مع التنبيهات
    latest_devices = Device.objects.order_by('-device_id')[:4]

    devices_with_alert = []
    for device in latest_devices:
        device_alerts = Alert.objects.filter(detection__reading__device=device)
        random_alert = random.choice(list(device_alerts)) if device_alerts.exists() else None
        devices_with_alert.append({
            'device': device,
            'alert': random_alert,
            'alert_severity': random_alert.detection.severity if random_alert else None,
        })

    # استهلاك الطاقة الاسبوعي
    arabic_days = {
        'Sunday': 'الأحد', 'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء',
        'Wednesday': 'الأربعاء', 'Thursday': 'الخميس',
        'Friday': 'الجمعة', 'Saturday': 'السبت',
    }

    today = timezone.now().date()
    start_date = today - timedelta(days=(today.weekday() + 1) % 7)

    days = []
    for i in range(7):
        current_date = start_date + timedelta(days=i)

        avg_power = DeviceReading.objects.filter(
            timestamp__date=current_date
        ).aggregate(avg=Avg('power_kw'))['avg']

        day_name_en = current_date.strftime('%A')
        days.append({
            'day': arabic_days[day_name_en],
            'energy': round(avg_power, 2) if avg_power else 0,
        })

    context = {
        'total_alerts_count': total_alerts_count,
        'all_alerts': all_alerts,
        'devices_with_alert': devices_with_alert,
        'days': days,
    }
    return render(request, 'dashboard/dashboard.html', context)
    