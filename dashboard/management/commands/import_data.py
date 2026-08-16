"""
سكربت استيراد بيانات النوتبوك النهائية داخل قاعدة بيانات جانقو
====================================================================
يشتغل كأمر Django: python manage.py import_data

ضعه بالمسار: dashboard/management/commands/import_data.py
(لازم مجلدين فاضيين فيهم __init__.py: management/ ثم management/commands/)

قبل التشغيل: انسخي ملف django_import.csv من نتيجة النوتبوك
إلى جذر مشروع EnerTrack (نفس مكان manage.py)
"""

import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from dashboard.models import (
    Household, Device, DeviceReading, ModelRegistry, AnomalyDetection, Alert
)


class Command(BaseCommand):
    help = "يستورد بيانات django_import.csv (نتيجة النوتبوك) لكل الجداول"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", type=str, default="django_import.csv",
            help="مسار ملف الـCSV (افتراضيًا: django_import.csv بجذر المشروع)"
        )

    def handle(self, *args, **options):
        filepath = options["file"]

        self.stdout.write(self.style.SUCCESS(f"بدء الاستيراد من: {filepath}"))

        # نسجل نسخة نموذج واحدة تُستخدم لكل نتائج هذا الاستيراد
        model_reg, _ = ModelRegistry.objects.get_or_create(
            model_version="xgb_classifier_v1",
            defaults={"model_type": "classifier"},
        )

        households_cache = {}   # household_id -> Household object
        devices_cache = {}      # device_id -> Device object

        rows_created = 0
        alerts_created = 0

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"عدد الصفوف بالملف: {len(rows)}")

        with transaction.atomic():
            for i, row in enumerate(rows, start=1):
                hh_id = int(row["household_id"])

                # 1) البيت — ننشئه مرة وحدة فقط لو ما انشأ قبل
                if hh_id not in households_cache:
                    household, _ = Household.objects.get_or_create(
                        household_id=hh_id,
                        defaults={
                            "region": row["region_name"],
                            "customer_category": row["customer_category"],
                        },
                    )
                    households_cache[hh_id] = household
                household = households_cache[hh_id]

                # 2) الجهاز — ننشئه مرة وحدة فقط لو ما انشأ قبل
                device_id = row["device_id"]
                if device_id not in devices_cache:
                    device, _ = Device.objects.get_or_create(
                        device_id=device_id,
                        defaults={
                            "household": household,
                            "device_type": row["device_type"],
                            "brand": row["device_brand"],
                            "model_name": row["device_model"],
                            "rated_power": float(row["rated_power"]),
                        },
                    )
                    devices_cache[device_id] = device
                device = devices_cache[device_id]

                # 3) القراءة
                reading = DeviceReading.objects.create(
                    device=device,
                    timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                    power_kw=float(row["power"]),
                    voltage=float(row["voltage"]),
                    temperature=float(row["device_temperature"]),
                    efficiency_ratio=float(row["efficiency_ratio"]),
                )

                # 4) نتيجة فحص الشذوذ
                detection = AnomalyDetection.objects.create(
                    reading=reading,
                    model_version=model_reg,
                    composite_score=float(row["composite_score"]),
                    severity=row["severity"],
                )
                rows_created += 1

                # 5) تنبيه تلقائي لو الخطورة عالية أو حرجة
                if row["severity"] in ("عالي", "حرج"):
                    Alert.objects.create(detection=detection, status="open")
                    alerts_created += 1

                if i % 2000 == 0:
                    self.stdout.write(f"...تمت معالجة {i} صف")

        self.stdout.write(self.style.SUCCESS(
            f"\nخلص الاستيراد بنجاح:\n"
            f"  بيوت: {len(households_cache)}\n"
            f"  أجهزة: {len(devices_cache)}\n"
            f"  قراءات + نتائج فحص: {rows_created}\n"
            f"  تنبيهات مولّدة: {alerts_created}"
        ))