"""
محاكي بيانات نظام إدارة الطاقة (للاختبار من التيرمنال فقط، بدون واجهة)
====================================================================
يشتغل كأمر Django: python manage.py simulate_stream --mode synthetic --speed 2 --anomaly_rate 0.05

ضعه بالمسار: dashboard/management/commands/simulate_stream.py
(نفس مجلد commands اللي فيه import_data.py)
"""

import time
import random
import numpy as np
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import Device, DeviceReading, AnomalyDetection, ModelRegistry, Alert

# إحصائيات كل نوع جهاز (نفس أرقام الترقية 1 من النوتبوك)
DEVICE_STATS = {
    "HVAC":         {"power_ratio_mean": 1.19,  "power_ratio_std": 0.65, "voltage_mean": 230.0, "voltage_std": 11.5},
    "Refrigerator": {"power_ratio_mean": 11.88, "power_ratio_std": 6.36, "voltage_mean": 230.0, "voltage_std": 11.5},
    "Dryer":        {"power_ratio_mean": 1.39,  "power_ratio_std": 0.75, "voltage_mean": 230.0, "voltage_std": 11.5},
    "Washer":       {"power_ratio_mean": 4.16,  "power_ratio_std": 2.26, "voltage_mean": 230.0, "voltage_std": 11.5},
}


class Command(BaseCommand):
    help = "يشغّل محاكي بيانات حي لاختبار الباك إند من التيرمنال، بدون واجهة"

    def add_arguments(self, parser):
        parser.add_argument("--mode", type=str, default="synthetic", choices=["synthetic"])
        parser.add_argument("--speed", type=float, default=2.0, help="ثواني بين كل قراءة")
        parser.add_argument("--anomaly_rate", type=float, default=0.05, help="نسبة حقن شذوذ متعمد")
        parser.add_argument("--count", type=int, default=0, help="عدد القراءات (0 = بلا نهاية)")

    def handle(self, *args, **options):
        speed = options["speed"]
        anomaly_rate = options["anomaly_rate"]
        count = options["count"]

        self.stdout.write(self.style.SUCCESS(
            f"بدء المحاكاة — كل {speed} ثانية — نسبة شذوذ متعمد {anomaly_rate*100:.0f}%"
        ))

        devices = list(Device.objects.all())
        if not devices:
            self.stdout.write(self.style.ERROR("ما فيه أجهزة بقاعدة البيانات — تأكدي إنك سوّيتي import_data أول"))
            return

        model_reg, _ = ModelRegistry.objects.get_or_create(
            model_version="rule_based_v1",
            defaults={"model_type": "statistical_rule"},
        )

        i = 0
        while True:
            i += 1
            device = random.choice(devices)
            stats = DEVICE_STATS.get(device.device_type, DEVICE_STATS["HVAC"])

            inject_anomaly = random.random() < anomaly_rate
            mult = 3.5 if inject_anomaly else 1.0
            power_ratio = max(0, np.random.normal(stats["power_ratio_mean"], stats["power_ratio_std"])) * mult
            power_kw = round(power_ratio * device.rated_power, 4)
            voltage = round(np.random.normal(stats["voltage_mean"], stats["voltage_std"]), 2)
            temperature = round(np.random.normal(45, 8), 1)
            efficiency = round(np.clip(np.random.normal(0.85, 0.1), 0.3, 1.0), 3)

            reading = DeviceReading.objects.create(
                device=device,
                timestamp=timezone.now(),
                power_kw=power_kw,
                voltage=voltage,
                temperature=temperature,
                efficiency_ratio=efficiency,
            )

            severity, score = self.evaluate_reading(power_kw, voltage, device)

            detection = AnomalyDetection.objects.create(
                reading=reading,
                model_version=model_reg,
                composite_score=score,
                severity=severity,
            )

            if severity in ("عالي", "حرج"):
                Alert.objects.create(detection=detection, status="open")
                self.stdout.write(self.style.WARNING(
                    f"[{i}] تنبيه [{severity}] — {device.device_type} ({device.device_id}) "
                    f"— power={power_kw}kW — درجة={score:.2f}"
                ))
            else:
                self.stdout.write(
                    f"[{i}] طبيعي — {device.device_type} ({device.device_id}) "
                    f"— power={power_kw}kW — درجة={score:.2f}"
                )

            if count and i >= count:
                self.stdout.write(self.style.SUCCESS(f"\nخلصت المحاكاة — {i} قراءة"))
                break

            time.sleep(speed)

    def evaluate_reading(self, power_kw, voltage, device):
        power_ratio = power_kw / device.rated_power if device.rated_power else 0
        stats = DEVICE_STATS.get(device.device_type, DEVICE_STATS["HVAC"])

        z_power = abs(power_ratio - stats["power_ratio_mean"]) / (stats["power_ratio_std"] or 1)
        z_voltage = abs(voltage - stats["voltage_mean"]) / (stats["voltage_std"] or 1)

        score = min(1.0, (z_power + z_voltage) / 8)

        if score < 0.15:
            severity = "طبيعي"
        elif score < 0.35:
            severity = "منخفض"
        elif score < 0.55:
            severity = "متوسط"
        elif score < 0.75:
            severity = "عالي"
        else:
            severity = "حرج"

        return severity, round(score, 4)