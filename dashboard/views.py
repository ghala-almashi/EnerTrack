from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Max
from datetime import timedelta
from .models import Device, Alert, DeviceReading, Forecast, MaintenanceRecommendation
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    # 1. جلب أحدث تاريخ قراءة ناتج عن المحاكاة
    latest_reading_time = DeviceReading.objects.aggregate(Max('timestamp'))['timestamp__max']
    
    # فلترة التنبيهات النشطة المرتبطة بآخر قراءات المحاكاة فقط (مثلاً خلال آخر ساعة من قراءات المحاكاة)
    if latest_reading_time:
        cutoff_time = latest_reading_time - timedelta(hours=1)
        active_alerts_qs = Alert.objects.filter(
            status='open',
            detection__reading__timestamp__gte=cutoff_time
        ).select_related('detection__reading__device').order_by('-detection__reading__timestamp')
    else:
        active_alerts_qs = Alert.objects.none()

    total_alerts_count = active_alerts_qs.count()
    
    # 2. أحدث 5 تنبيهات ناتجة عن المحاكاة
    active_alerts = []
    for alert in active_alerts_qs[:5]:
        device = alert.detection.reading.device
        severity = alert.detection.severity
        
        severity_class = 'high' if severity in ['حرج', 'عالي'] else ('medium' if severity == 'متوسط' else 'low')
            
        active_alerts.append({
            'device_label': f"{device.device_type} ({device.device_id})",
            'message': f"ارتفاع في الاستهلاك / شذوذ ({severity})",
            'severity_class': severity_class
        })

    # 3. الأجهزة لشريط SideBar
    all_devices = Device.objects.all()[:6]
    devices_with_alert = [
        {'device': d, 'label': f"{d.device_type} - {d.brand} ({d.device_id})"}
        for d in all_devices
    ]

    # 4. حساب استهلاك الأيام السبعة الأخيرة
    arabic_days = {
        'Sunday': 'الأحد', 'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء',
        'Wednesday': 'الأربعاء', 'Thursday': 'الخميس',
        'Friday': 'الجمعة', 'Saturday': 'السبت',
    }

    days = []
    if latest_reading_time:
        end_date = latest_reading_time.date()
        for i in range(6, -1, -1):
            target_date = end_date - timedelta(days=i)
            avg_power = DeviceReading.objects.filter(
                timestamp__date=target_date
            ).aggregate(avg=Avg('power_kw'))['avg']
            
            day_name = arabic_days.get(target_date.strftime('%A'), target_date.strftime('%A'))
            days.append({
                'day': day_name,
                'energy': round(avg_power, 2) if avg_power else 0
            })

    # 5. التنبؤ بالأسبوع القادم
    forecast_qs = Forecast.objects.order_by('target_date')[:7]
    forecast_days = [
        {
            'day': arabic_days.get(f.target_date.strftime('%A'), f.target_date.strftime('%A')),
            'energy': round(f.p50, 2)
        }
        for f in forecast_qs
    ]

    context = {
        'total_alerts_count': total_alerts_count,
        'active_alerts': active_alerts,
        'devices_with_alert': devices_with_alert,
        'days': days,
        'forecast_days': forecast_days,
    }
    return render(request, 'dashboard/dashboard.html', context)


def device_detail_view(request, device_id):
    device = get_object_or_404(Device, device_id=device_id)

    # أحدث قراءة للجهاز
    latest_reading = DeviceReading.objects.filter(device=device).order_by('-timestamp').first()

    # التنبيه والمقترحات
    alert = Alert.objects.filter(detection__reading__device=device, status='open').order_by('-detection__reading__timestamp').first()
    recommendation = MaintenanceRecommendation.objects.filter(alert=alert).first() if alert else None

    # حساب استهلاك الأسبوع الحالي للجهاز
    arabic_days = {
        'Sunday': 'الأحد', 'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء',
        'Wednesday': 'الأربعاء', 'Thursday': 'الخميس',
        'Friday': 'الجمعة', 'Saturday': 'السبت',
    }

    days = []
    if latest_reading:
        end_date = latest_reading.timestamp.date()
        for i in range(6, -1, -1):
            target_date = end_date - timedelta(days=i)
            avg_power = DeviceReading.objects.filter(
                device=device,
                timestamp__date=target_date
            ).aggregate(avg=Avg('power_kw'))['avg']
            
            day_name = arabic_days.get(target_date.strftime('%A'), target_date.strftime('%A'))
            days.append({
                'day': day_name,
                'energy': round(avg_power, 2) if avg_power else 0
            })

    context = {
        'device': device,
        'device_label': f"{device.device_type} ({device.device_id})",
        'device_icon': '⚡',
        'latest_reading': latest_reading,
        'alert': alert,
        'latest_severity': alert.detection.severity if alert else 'طبيعي',
        'recommendation': recommendation,
        'recommendation_sentence': recommendation.action_required if recommendation else '',
        'days': days,
    }
    return render(request, 'dashboard/device_detail.html', context)
