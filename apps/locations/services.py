from .models import District, Province


def get_homepage_location_sample():
    provinces = Province.objects.count()
    districts = District.objects.count()
    sample_districts = list(District.objects.select_related("province").order_by("name")[:3])
    return {
        "province_count": provinces,
        "district_count": districts,
        "sample_districts": sample_districts,
    }
