def build_tourist_destination_json_ld(destination, image_url=None):
    data = {
        "@context": "https://schema.org",
        "@type": "TouristAttraction",
        "name": destination.title,
        "description": destination.summary or destination.description,
    }
    if destination.region:
        data["address"] = {"@type": "PostalAddress", "addressRegion": destination.region}
    if image_url:
        data["image"] = image_url
    return data
